"""
智能写字机系统 - 校准模块

功能：
1. 生成 ArUco 标记
2. 使用 PaddleOCR 进行图像矫正
3. 检测 ArUco 标记并计算仿射变换矩阵
4. 图像坐标到写字机物理坐标的转换
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import pickle

from src.core import SystemConfig


class ArUcoMarkerGenerator:
    """ArUco 标记生成器"""

    # ArUco 字典类型
    ARUCO_DICT = {
        'DICT_4X4_50': cv2.aruco.DICT_4X4_50,
        'DICT_4X4_100': cv2.aruco.DICT_4X4_100,
        'DICT_5X5_50': cv2.aruco.DICT_5X5_50,
        'DICT_5X5_100': cv2.aruco.DICT_5X5_100,
        'DICT_6X6_50': cv2.aruco.DICT_6X6_50,
        'DICT_6X6_100': cv2.aruco.DICT_6X6_100,
        'DICT_7X7_50': cv2.aruco.DICT_7X7_50,
        'DICT_7X7_100': cv2.aruco.DICT_7X7_100,
    }

    def __init__(self, marker_size: int = 100, dict_name: str = 'DICT_6X6_250'):
        """
        初始化 ArUco 标记生成器

        Args:
            marker_size: 标记大小（像素）
            dict_name: ArUco 字典名称
        """
        self.marker_size = marker_size
        self.dict_name = dict_name

        # 获取 ArUco 字典
        try:
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(self.ARUCO_DICT[dict_name])
        except KeyError:
            print(f"警告：未知字典 {dict_name}，使用默认字典 DICT_6X6_250")
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)

    def generate_marker(self, marker_id: int, save_path: Optional[str] = None) -> np.ndarray:
        """
        生成单个 ArUco 标记

        Args:
            marker_id: 标记 ID
            save_path: 保存路径（可选）

        Returns:
            标记图像
        """
        marker_image = cv2.aruco.generateImage(self.aruco_dict, marker_id, self.marker_size)

        if save_path:
            cv2.imwrite(save_path, marker_image)
            print(f"✓ 标记已保存到：{save_path}")

        return marker_image

    def generate_marker_board(self, marker_ids: List[int], save_path: Optional[str] = None,
                             margins: int = 10, marker_size_mm: float = 30.0) -> np.ndarray:
        """
        生成 ArUco 标记板（多个标记排列）

        Args:
            marker_ids: 标记 ID 列表
            save_path: 保存路径（可选）
            margins: 边距（像素）
            marker_size_mm: 标记物理尺寸（毫米）

        Returns:
            标记板图像
        """
        num_markers = len(marker_ids)
        num_cols = int(np.ceil(np.sqrt(num_markers)))
        num_rows = int(np.ceil(num_markers / num_cols))

        marker_with_margin = self.marker_size + margins
        board_width = num_cols * marker_with_margin + margins
        board_height = num_rows * marker_with_margin + margins

        board = np.ones((board_height, board_width), dtype=np.uint8) * 255

        for i, marker_id in enumerate(marker_ids):
            row = i // num_cols
            col = i % num_cols
            x = col * marker_with_margin + margins
            y = row * marker_with_margin + margins

            marker = cv2.aruco.generateImage(self.aruco_dict, marker_id, self.marker_size)
            board[y:y+self.marker_size, x:x+self.marker_size] = marker

        if save_path:
            cv2.imwrite(save_path, board)
            print(f"✓ 标记板已保存到：{save_path}")

        return board


class ImageUnwarp:
    """图像矫正器"""

    def __init__(self):
        """初始化图像矫正器"""
        pass

    def unwarp_image(self, image: np.ndarray, points: List[Tuple[int, int]], 
                     output_size: Tuple[int, int]) -> np.ndarray:
        """
        使用透视变换矫正图像

        Args:
            image: 输入图像
            points: 四个角点坐标 [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
            output_size: 输出图像大小 (width, height)

        Returns:
            矫正后的图像
        """
        if len(points) != 4:
            raise ValueError("需要 4 个角点坐标")

        src_points = np.array(points, dtype=np.float32)
        dst_points = np.array([
            [0, 0],
            [output_size[0] - 1, 0],
            [output_size[0] - 1, output_size[1] - 1],
            [0, output_size[1] - 1]
        ], dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        warped = cv2.warpPerspective(image, matrix, output_size)

        return warped

    def unwarp_image_auto(self, image: np.ndarray) -> np.ndarray:
        """
        无角点信息时的直通处理：不做透视矫正，原样返回图像。

        当调用方没有四个角点坐标（例如自动查词/自动抄写流程）时使用。
        保留 unwarper 接口是为了将来接入自动角点检测时的占位。

        Args:
            image: 输入图像

        Returns:
            原样返回的图像（未矫正）
        """
        return image


class Calibrator:
    """写字机校准器"""

    def __init__(self, marker_size: float = 30.0):
        """
        初始化校准器

        Args:
            marker_size: ArUco 标记物理尺寸（毫米）
        """
        self.marker_size = marker_size
        self.transformation_matrix = None
        self.inverse_matrix = None

    def detect_markers(self, image: np.ndarray) -> Dict[int, Tuple[float, float]]:
        """
        检测图像中的 ArUco 标记

        Args:
            image: 输入图像

        Returns:
            标记 ID 到中心坐标的字典
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        parameters = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        
        corners, ids, _ = detector.detectMarkers(gray)

        marker_centers = {}
        if ids is not None:
            for i, corner in enumerate(corners):
                marker_id = ids[i][0]
                center = np.mean(corner[0], axis=0)
                marker_centers[marker_id] = (float(center[0]), float(center[1]))

        return marker_centers

    def compute_transformation(self, image_points: Dict[int, Tuple[float, float]],
                               physical_points: Dict[int, Tuple[float, float]]) -> bool:
        """
        计算图像坐标到物理坐标的变换矩阵

        Args:
            image_points: 图像坐标 {marker_id: (x, y)}
            physical_points: 物理坐标 {marker_id: (x, y)} 单位：毫米

        Returns:
            是否成功计算
        """
        common_ids = set(image_points.keys()) & set(physical_points.keys())
        
        if len(common_ids) < 3:
            print("错误：至少需要 3 个共同标记点")
            return False

        src = np.array([image_points[mid] for mid in common_ids], dtype=np.float32)
        dst = np.array([physical_points[mid] for mid in common_ids], dtype=np.float32)

        self.transformation_matrix, _ = cv2.estimateAffine2D(src, dst)
        self.inverse_matrix, _ = cv2.estimateAffine2D(dst, src)

        return True

    def calibrate_from_image(self, image_path: str, marker_positions: Dict[int, Tuple[float, float]],
                            save_path: Optional[str] = None) -> bool:
        """
        从图像进行校准

        Args:
            image_path: 图像路径
            marker_positions: 标记的物理位置 {marker_id: (x, y)}
            save_path: 校准数据保存路径

        Returns:
            是否成功校准
        """
        image = cv2.imread(image_path)
        if image is None:
            print(f"错误：无法读取图像 {image_path}")
            return False

        image_points = self.detect_markers(image)
        
        if len(image_points) < 3:
            print(f"错误：只检测到 {len(image_points)} 个标记，至少需要 3 个")
            return False

        success = self.compute_transformation(image_points, marker_positions)
        
        if success and save_path:
            self.save_calibration(save_path)
            print(f"✓ 校准数据已保存到：{save_path}")

        return success

    def image_to_physical(self, image_x: float, image_y: float) -> Tuple[float, float]:
        """
        将图像坐标转换为物理坐标

        Args:
            image_x: 图像 X 坐标
            image_y: 图像 Y 坐标

        Returns:
            物理坐标 (x, y) 单位：毫米
        """
        if self.transformation_matrix is None:
            raise ValueError("未进行校准")

        point = np.array([[image_x, image_y]], dtype=np.float32)
        physical = cv2.transform(point.reshape(1, 1, 2), self.transformation_matrix)
        
        return float(physical[0][0][0]), float(physical[0][0][1])

    def physical_to_image(self, physical_x: float, physical_y: float) -> Tuple[float, float]:
        """
        将物理坐标转换为图像坐标

        Args:
            physical_x: 物理 X 坐标（毫米）
            physical_y: 物理 Y 坐标（毫米）

        Returns:
            图像坐标 (x, y)
        """
        if self.inverse_matrix is None:
            raise ValueError("未进行校准")

        point = np.array([[physical_x, physical_y]], dtype=np.float32)
        image = cv2.transform(point.reshape(1, 1, 2), self.inverse_matrix)
        
        return float(image[0][0][0]), float(image[0][0][1])

    def save_calibration(self, path: str):
        """保存校准数据"""
        data = {
            'transformation_matrix': self.transformation_matrix,
            'inverse_matrix': self.inverse_matrix,
            'marker_size': self.marker_size
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)

    def load_calibration(self, path: str) -> bool:
        """加载校准数据"""
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            self.transformation_matrix = data['transformation_matrix']
            self.inverse_matrix = data['inverse_matrix']
            self.marker_size = data.get('marker_size', self.marker_size)
            
            return True
        except Exception as e:
            print(f"错误：加载校准数据失败：{e}")
            return False

    def generate_markers_gcode(self, marker_positions: Dict[int, Tuple[float, float]],
                               marker_size_mm: float, gcode_path: str,
                               preview_path: Optional[str] = None) -> str:
        """
        生成绘制 ArUco 标记的 Gcode

        Args:
            marker_positions: 标记位置 {marker_id: (x, y)}
            marker_size_mm: 标记尺寸（毫米）
            gcode_path: Gcode 保存路径
            preview_path: 预览图保存路径（可选）

        Returns:
            Gcode 字符串
        """
        gcode_lines = []
        gcode_lines.append("; Generated ArUco markers Gcode")
        gcode_lines.append(f"; Marker size: {marker_size_mm}mm")
        gcode_lines.append("")
        
        z_pen_up = SystemConfig.Z_PEN_UP
        z_pen_down = SystemConfig.Z_PEN_DOWN
        feed_rate = SystemConfig.FEED_RATE

        for marker_id, (x, y) in marker_positions.items():
            half_size = marker_size_mm / 2
            
            # 移动到标记左上角
            gcode_lines.append(f"; Marker {marker_id}")
            gcode_lines.append(f"G0 X{x - half_size} Y{y - half_size} Z{z_pen_up} F{feed_rate}")
            
            # 下笔
            gcode_lines.append(f"G0 Z{z_pen_down}")
            
            # 绘制正方形
            gcode_lines.append(f"G0 X{x + half_size}")
            gcode_lines.append(f"G0 Y{y + half_size}")
            gcode_lines.append(f"G0 X{x - half_size}")
            gcode_lines.append(f"G0 Y{y - half_size}")
            gcode_lines.append(f"G0 X{x + half_size}")
            
            # 抬笔
            gcode_lines.append(f"G0 Z{z_pen_up}")
            gcode_lines.append("")

        gcode = "\n".join(gcode_lines)

        with open(gcode_path, 'w') as f:
            f.write(gcode)

        if preview_path:
            self._generate_preview(marker_positions, marker_size_mm, preview_path)

        return gcode

    def _generate_preview(self, marker_positions: Dict[int, Tuple[float, float]],
                         marker_size_mm: float, preview_path: str):
        """生成预览图"""
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(8, 10))
        ax.set_xlim(-10, SystemConfig.WORK_AREA_X + 10)
        ax.set_ylim(SystemConfig.WORK_AREA_Y + 10, -10)
        ax.set_aspect('equal')
        
        for marker_id, (x, y) in marker_positions.items():
            half_size = marker_size_mm / 2
            rect = plt.Rectangle(
                (x - half_size, y - half_size),
                marker_size_mm, marker_size_mm,
                fill=False, edgecolor='blue', linewidth=2
            )
            ax.add_patch(rect)
            ax.text(x, y, str(marker_id), ha='center', va='center', fontsize=12, color='red')
        
        plt.grid(True, alpha=0.3)
        plt.xlabel('X (mm)')
        plt.ylabel('Y (mm)')
        plt.title('ArUco Markers Preview')
        plt.savefig(preview_path, dpi=150, bbox_inches='tight')
        plt.close()

    def generate_corner_marker_paper(self, frame_width_mm: float, frame_height_mm: float,
                                      marker_size_mm: float = 30.0, margin_mm: float = 5.0,
                                      save_path: Optional[str] = None) -> np.ndarray:
        dpi = 300
        mm_to_px = dpi / 25.4
        paper_w_px = int(frame_width_mm * mm_to_px)
        paper_h_px = int(frame_height_mm * mm_to_px)
        marker_px = int(marker_size_mm * mm_to_px)
        margin_px = int(margin_mm * mm_to_px)

        paper = np.ones((paper_h_px, paper_w_px), dtype=np.uint8) * 255

        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        corners = [
            (margin_px, margin_px),
            (paper_w_px - margin_px - marker_px, margin_px),
            (paper_w_px - margin_px - marker_px, paper_h_px - margin_px - marker_px),
            (margin_px, paper_h_px - margin_px - marker_px),
        ]

        for i, (cx, cy) in enumerate(corners):
            marker_img = cv2.aruco.generateImage(aruco_dict, i, marker_px)
            paper[cy:cy + marker_px, cx:cx + marker_px] = marker_img

            font = cv2.FONT_HERSHEY_SIMPLEX
            label = f"ID:{i}"
            text_size = cv2.getTextSize(label, font, 0.4, 1)[0]
            cv2.putText(paper, label, (cx + (marker_px - text_size[0]) // 2,
                                       cy + marker_px + text_size[1] + 4),
                        font, 0.4, 0, 1, cv2.LINE_AA)

        frame_pts = np.array([
            [margin_px // 2, margin_px // 2],
            [paper_w_px - margin_px // 2, margin_px // 2],
            [paper_w_px - margin_px // 2, paper_h_px - margin_px // 2],
            [margin_px // 2, paper_h_px - margin_px // 2]
        ], dtype=np.int32)
        cv2.polylines(paper, [frame_pts], True, 0, 2)

        if save_path:
            cv2.imwrite(save_path, paper)
            print(f"✓ 四角标记定位纸已保存到：{save_path}")

        return paper

    def check_matrix_variance(self, new_matrix: np.ndarray,
                               threshold_mm: float = 2.0,
                               threshold_deg: float = 2.0) -> Dict[str, Any]:
        if self.transformation_matrix is None:
            return {'valid': False, 'error': '未进行初始校准'}

        old_mat = self.transformation_matrix
        if old_mat.shape == (2, 3):
            old_mat = np.vstack([old_mat, [0, 0, 1]])
        if new_matrix.shape == (2, 3):
            new_matrix = np.vstack([new_matrix, [0, 0, 1]])

        try:
            diff_mat = new_matrix @ np.linalg.inv(old_mat)
        except np.linalg.LinAlgError:
            return {'valid': False, 'error': '矩阵求逆失败'}

        tx = diff_mat[0, 2]
        ty = diff_mat[1, 2]
        translation_mm = np.sqrt(tx ** 2 + ty ** 2)

        angle_rad = np.arctan2(diff_mat[1, 0], diff_mat[0, 0])
        angle_deg = np.degrees(angle_rad)

        is_ok = translation_mm <= threshold_mm and abs(angle_deg) <= threshold_deg

        return {
            'valid': True,
            'ok': is_ok,
            'translation_mm': round(translation_mm, 3),
            'rotation_deg': round(angle_deg, 3),
            'threshold_mm': threshold_mm,
            'threshold_deg': threshold_deg,
            'warning': None if is_ok else f'位置偏移 {translation_mm:.1f}mm / 旋转 {angle_deg:.1f}° 超过阈值，请重新校准'
        }


__all__ = ['ArUcoMarkerGenerator', 'ImageUnwarp', 'Calibrator']
