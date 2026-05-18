"""
OneDrive备份模块 - 使用Microsoft Graph API备份已会词到OneDrive

功能：
1. OAuth2授权流程（设备码流，无需公网回调）
2. 全量备份已会词到OneDrive（JSON格式，带版本号）
3. 列出备份历史
4. 从OneDrive恢复（合并到本地数据库）
"""

import json
import os
import time
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import requests

TOKEN_FILE = "onedrive_token.json"
BACKUP_FOLDER = "Apps/DreamWord"

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class OneDriveBackup:
    def __init__(self, client_id: str, db_path: str = "known_words.db"):
        self.client_id = client_id
        self.db_path = db_path
        self.token_path = TOKEN_FILE
        self._tokens = None

    def _load_tokens(self) -> Optional[Dict[str, Any]]:
        if self._tokens is not None:
            return self._tokens
        if not os.path.exists(self.token_path):
            return None
        try:
            with open(self.token_path, 'r', encoding='utf-8') as f:
                self._tokens = json.load(f)
            return self._tokens
        except Exception:
            return None

    def _save_tokens(self, tokens: Dict[str, Any]):
        self._tokens = tokens
        with open(self.token_path, 'w', encoding='utf-8') as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)

    def get_device_code(self) -> Dict[str, Any]:
        resp = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode",
            data={
                "client_id": self.client_id,
                "scope": "Files.ReadWrite.AppFolder offline_access"
            },
            timeout=30
        )
        if resp.status_code != 200:
            raise Exception(f"获取设备码失败: {resp.text}")
        return resp.json()

    def poll_token(self, device_code: str) -> Optional[Dict[str, Any]]:
        resp = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": self.client_id,
                "device_code": device_code
            },
            timeout=30
        )
        if resp.status_code == 200:
            tokens = resp.json()
            tokens['expires_at'] = time.time() + tokens.get('expires_in', 3600) - 60
            self._save_tokens(tokens)
            return tokens
        error = resp.json().get('error', '')
        if error == 'authorization_pending':
            return None
        if error == 'slow_down':
            return None
        raise Exception(f"获取token失败: {resp.text}")

    def _ensure_token(self) -> str:
        tokens = self._load_tokens()
        if not tokens:
            raise Exception("未授权，请先完成OneDrive授权")
        if time.time() > tokens.get('expires_at', 0):
            self._refresh_token()
            tokens = self._load_tokens()
        return tokens['access_token']

    def _refresh_token(self):
        tokens = self._load_tokens()
        if not tokens or 'refresh_token' not in tokens:
            raise Exception("无refresh_token，请重新授权")
        resp = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "refresh_token": tokens['refresh_token']
            },
            timeout=30
        )
        if resp.status_code != 200:
            raise Exception(f"刷新token失败: {resp.text}")
        new_tokens = resp.json()
        new_tokens['expires_at'] = time.time() + new_tokens.get('expires_in', 3600) - 60
        self._save_tokens(new_tokens)
        self._tokens = new_tokens

    def _graph_get(self, path: str) -> Any:
        token = self._ensure_token()
        resp = requests.get(
            f"{GRAPH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        if resp.status_code == 401:
            self._refresh_token()
            token = self._ensure_token()
            resp = requests.get(
                f"{GRAPH_BASE}{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
        if resp.status_code != 200:
            raise Exception(f"Graph API错误: {resp.status_code} {resp.text}")
        return resp.json()

    def _graph_put(self, path: str, content: bytes) -> Any:
        token = self._ensure_token()
        resp = requests.put(
            f"{GRAPH_BASE}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            data=content,
            timeout=60
        )
        if resp.status_code == 401:
            self._refresh_token()
            token = self._ensure_token()
            resp = requests.put(
                f"{GRAPH_BASE}{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                data=content,
                timeout=60
            )
        if resp.status_code not in (200, 201):
            raise Exception(f"上传失败: {resp.status_code} {resp.text}")
        return resp.json()

    def _graph_patch(self, path: str, content: bytes) -> Any:
        token = self._ensure_token()
        resp = requests.patch(
            f"{GRAPH_BASE}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            data=content,
            timeout=30
        )
        if resp.status_code not in (200, 201):
            raise Exception(f"更新失败: {resp.status_code} {resp.text}")
        return resp.json()

    def _graph_post(self, path: str, content: bytes) -> Any:
        token = self._ensure_token()
        resp = requests.post(
            f"{GRAPH_BASE}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            data=content,
            timeout=30
        )
        if resp.status_code not in (200, 201):
            raise Exception(f"请求失败: {resp.status_code} {resp.text}")
        return resp.json()

    def is_authorized(self) -> bool:
        tokens = self._load_tokens()
        if not tokens:
            return False
        try:
            self._ensure_token()
            return True
        except Exception:
            return False

    def _get_all_words(self) -> List[str]:
        if not os.path.exists(self.db_path):
            return []
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT word FROM known_words ORDER BY word')
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def _get_local_version(self) -> int:
        meta_path = Path(self.db_path).parent / "backup_meta.json"
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('last_backup_version', 0)
            except Exception:
                return 0
        return 0

    def _set_local_version(self, version: int):
        meta_path = Path(self.db_path).parent / "backup_meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({'last_backup_version': version}, f)

    def _ensure_folder(self):
        try:
            self._graph_get("/me/drive/special/approot/children")
        except Exception:
            pass

    def backup(self) -> Dict[str, Any]:
        words = self._get_all_words()
        local_version = self._get_local_version()
        new_version = local_version + 1

        backup_data = {
            "version": new_version,
            "timestamp": datetime.now().isoformat(),
            "word_count": len(words),
            "words": words
        }

        self._ensure_folder()

        filename = f"known_words_v{new_version}.json"
        content = json.dumps(backup_data, ensure_ascii=False, indent=2).encode('utf-8')

        self._graph_put(
            f"/me/drive/special/approot:/{filename}:/content",
            content
        )

        try:
            meta_content = json.dumps({
                "last_backup_version": new_version,
                "last_backup_time": backup_data["timestamp"],
                "last_backup_count": len(words)
            }).encode('utf-8')
            self._graph_put(
                "/me/drive/special/approot:/backup_meta.json:/content",
                meta_content
            )
        except Exception:
            pass

        self._set_local_version(new_version)

        return {
            "success": True,
            "version": new_version,
            "word_count": len(words),
            "timestamp": backup_data["timestamp"]
        }

    def list_backups(self) -> List[Dict[str, Any]]:
        try:
            result = self._graph_get("/me/drive/special/approot/children")
        except Exception:
            return []

        backups = []
        for item in result.get('value', []):
            name = item.get('name', '')
            if name.startswith('known_words_v') and name.endswith('.json'):
                backups.append({
                    'name': name,
                    'id': item.get('id', ''),
                    'size': item.get('size', 0),
                    'last_modified': item.get('lastModifiedDateTime', ''),
                    'download_url': item.get('@content.downloadUrl', '')
                })
        backups.sort(key=lambda x: x['name'], reverse=True)
        return backups

    def restore(self, backup_name: Optional[str] = None, merge: bool = True) -> Dict[str, Any]:
        if backup_name:
            path = f"/me/drive/special/approot:/{backup_name}:/content"
        else:
            meta = self._graph_get("/me/drive/special/approot:/backup_meta.json:/content")
            path = f"/me/drive/special/approot:/known_words_v{meta['last_backup_version']}.json:/content"

        token = self._ensure_token()
        resp = requests.get(
            f"{GRAPH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60
        )
        if resp.status_code != 200:
            raise Exception(f"下载备份失败: {resp.status_code}")

        backup_data = resp.json()
        cloud_words = set(w.lower() for w in backup_data.get('words', []))

        if merge:
            local_words = set(w.lower() for w in self._get_all_words())
            merged = local_words | cloud_words
            self._write_words(merged)
            return {
                "success": True,
                "action": "merged",
                "local_count": len(local_words),
                "cloud_count": len(cloud_words),
                "merged_count": len(merged),
                "new_words": len(merged - local_words),
                "version": backup_data.get('version', 0)
            }
        else:
            self._write_words(cloud_words)
            return {
                "success": True,
                "action": "replaced",
                "word_count": len(cloud_words),
                "version": backup_data.get('version', 0)
            }

    def _write_words(self, words: set):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS known_words (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT UNIQUE NOT NULL, add_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
            cursor.execute('DELETE FROM known_words')
            for word in sorted(words):
                cursor.execute('INSERT OR IGNORE INTO known_words (word) VALUES (?)', (word,))
            conn.commit()
        finally:
            conn.close()

    def disconnect(self):
        self._tokens = None
        if os.path.exists(self.token_path):
            os.remove(self.token_path)
