"""
校准模块 - 用于写字机的视觉校准

功能：
1. 生成ArUco标记
2. 使用PaddleOCR进行图像矫正
3. 检测ArUco标记并计算仿射变换矩阵
4. 图像坐标到写字机物理坐标的转换
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List
import pickle


class ArUcoMarkerGenerator:
    """ArUco标记生成器"""

    # ArUco字典类型
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
        初始化ArUco标记生成器

        Args:
            marker_size: 标记大小（像素）
            dict_name: ArUco字典名称
        """
        self.marker_size = marker_size
        self.dict_name = dict_name

        # 获取ArUco字典
        try:
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(self.ARUCO_DICT[dict_name])
        except KeyError:
            print(f"警告: 未知字典 {dict_name}，使用默认字典 DICT_6X6_250")
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)

    def generate_marker(self, marker_id: int, save_path: Optional[str] = None) -> np.ndarray:
        """
        生成单个ArUco标记

        Args:
            marker_id: 标记ID
            save_path: 保存路径（可选）

        Returns:
            标记图像
        """
        # 生成标记图像
        marker_image = cv2.aruco.generateImage(self.aruco_dict, marker_id, self.marker_size)

        # 保存图像
        if save_path:
            cv2.imwrite(save_path, marker_image)
            print(f"✓ 标记已保存到: {save_path}")

        return marker_image

    def generate_marker_board(self, marker_ids: List[int], save_path: Optional[str] = None,
                             margins: int = 10, marker_size_mm: float = 30.0) -> np.ndarray:
        """
        生成ArUco标记板（多个标记排列）

        Args:
            marker_ids: 标记ID列表
            save_path: 保存路径（可选）
            margins: 边距（像素）
            marker_size_mm: 标记物理尺寸（毫米）

        Returns:
            标记板图像
        """
        num_markers = len(marker_ids)
        num_cols = int(np.ceil(np.sqrt(num_markers)))
        num_rows = int(np.ceil(num_markers / num_cols))

        # 计算标记板大小
        marker_with_margin = self.marker_size + margins
        board_width = num_cols * marker_with_margin + margins
        board_height = num_rows * marker_with_margin + margins

        # 创建空白画布
        board = np.ones((board_height, board_width), dtype=np.uint8) * 255

        # 放置标记
        for i, marker_id in enumerate(marker_ids):
            row = i // num_cols
            col = i % num_cols

            # 生成标记
            marker = self.generate_marker(marker_id)

            # 计算位置
            y = row * marker_with_margin + margins
            x = col * marker_with_margin + margins

            # 放置标记
            board[y:y+self.marker_size, x:x+self.marker_size] = marker

        # 保存图像
        if save_path:
            cv2.imwrite(save_path, board)
            print(f"✓ 标记板已保存到: {save_path}")

        return board


class ImageUnwarp:
    """图像矫正 - 使用PaddleOCR文本图像矫正模块"""

    def __init__(self):
        """初始化图像矫正器"""
        try:
            from paddleocr import PPStructure
            print("正在初始化PaddleOCR...")
            self.ocr_engine = PPStructure(show_log=False)
            self.available = True
            print("✓ PaddleOCR初始化成功")
        except Exception as e:
            print(f"警告: PaddleOCR初始化失败: {e}")
            print("将使用传统矫正方法")
            self.ocr_engine = None
            self.available = False

    def unwarp_image(self, image: np.ndarray) -> np.ndarray:
        """
        矫正图像

        Args:
            image: 输入图像

        Returns:
            矫正后的图像
        """
        if not self.available or self.ocr_engine is None:
            # 使用传统方法
            return self._unwarp_traditional(image)

        try:
            # 使用PaddleOCR进行矫正
            result = self.ocr_engine(image)

            # 如果检测到文本区域，尝试矫正
            if result and len(result) > 0:
                # 这里简化处理，实际应该根据检测结果进行透视变换
                # 暂时返回原图
                return image
            else:
                return image

        except Exception as e:
            print(f"PaddleOCR矫正失败: {e}，使用传统方法")
            return self._unwarp_traditional(image)

    def _unwarp_traditional(self, image: np.ndarray) -> np.ndarray:
        """
        传统图像矫正方法

        Args:
            image: 输入图像

        Returns:
            矫正后的图像
        """
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return image

        # 找到最大轮廓
        max_contour = max(contours, key=cv2.contourArea)

        # 近似多边形
        epsilon = 0.02 * cv2.arcLength(max_contour, True)
        approx = cv2.approxPolyDP(max_contour, epsilon, True)

        # 如果找到了4个角点
        if len(approx) == 4:
            # 获取角点坐标
            points = approx.reshape(4, 2).astype(np.float32)

            # 排序角点（左上、右上、右下、左下）
            points = self._order_points(points)

            # 计算新图像的尺寸
            width_a = np.sqrt(((points[2][0] - points[3][0]) ** 2) + ((points[2][1] - points[3][1]) ** 2))
            width_b = np.sqrt(((points[1][0] - points[0][0]) ** 2) + ((points[1][1] - points[0][1]) ** 2))
            max_width = max(int(width_a), int(width_b))

            height_a = np.sqrt(((points[1][0] - points[2][0]) ** 2) + ((points[1][1] - points[2][1]) ** 2))
            height_b = np.sqrt(((points[0][0] - points[3][0]) ** 2) + ((points[0][1] - points[3][1]) ** 2))
            max_height = max(int(height_a), int(height_b))

            # 目标点
            dst = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype=np.float32)

            # 计算透视变换矩阵
            M = cv2.getPerspectiveTransform(points, dst)

            # 执行透视变换
            warped = cv2.warpPerspective(image, M, (max_width, max_height))

            return warped
        else:
            return image

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """
        排序四个角点

        Args:
            pts: 4个角点

        Returns:
            排序后的角点（左上、右上、右下、左下）
        """
        rect = np.zeros((4, 2), dtype=np.float32)

        # 根据x坐标排序
        # 最小的x是左边的点，最大的x是右边的点
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # 左上
        rect[2] = pts[np.argmax(s)]  # 右下

        # 根据差值排序
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # 右上
        rect[3] = pts[np.argmax(diff)]  # 左下

        return rect


class Calibrator:
    """校准器 - 使用ArUco标记进行校准"""

    def __init__(self, marker_size: float = 30.0, dict_name: str = 'DICT_6X6_250'):
        """
        初始化校准器

        Args:
            marker_size: ArUco标记的物理尺寸（毫米）
            dict_name: ArUco字典名称
        """
        self.marker_size = marker_size
        self.dict_name = dict_name

        # 初始化ArUco检测器
        try:
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(
                ArUcoMarkerGenerator.ARUCO_DICT.get(dict_name, cv2.aruco.DICT_6X6_250)
            )
            self.aruco_params = cv2.aruco.DetectorParameters()
            self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        except AttributeError:
            # 兼容旧版OpenCV
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(
                ArUcoMarkerGenerator.ARUCO_DICT.get(dict_name, cv2.aruco.DICT_6X6_250)
            )
            self.aruco_params = cv2.aruco.DetectorParameters_create()
            self.detector = None

        # 初始化图像矫正器
        self.unwarper = ImageUnwarp()

        # 校准数据
        self.camera_matrix = None
        self.dist_coeffs = None
        self.transformation_matrix = None

        # 物理工作区域（毫米）- 默认使用 A1 mini 的尺寸
        self.work_area_width = 256.0  # x方向
        self.work_area_height = 256.0  # y方向

    def detect_markers(self, image: np.ndarray) -> Tuple[List[np.ndarray], List[int]]:
        """
        检测图像中的ArUco标记

        Args:
            image: 输入图像

        Returns:
            (corners, ids): 标记角点和ID列表
        """
        try:
            if self.detector is not None:
                # OpenCV 4.7+
                corners, ids, rejected = self.detector.detectMarkers(image)
            else:
                # OpenCV 4.6及以下
                corners, ids, rejected = cv2.aruco.detectMarkers(
                    image,
                    self.aruco_dict,
                    parameters=self.aruco_params
                )

            if ids is not None:
                print(f"✓ 检测到 {len(ids)} 个ArUco标记")
            else:
                print("✗ 未检测到ArUco标记")

            return corners, ids if ids is not None else []

        except Exception as e:
            print(f"检测ArUco标记失败: {e}")
            return [], []

    def calculate_transformation_matrix(
        self,
        image: np.ndarray,
        marker_positions: dict
    ) -> Optional[np.ndarray]:
        """
        计算仿射变换矩阵

        Args:
            image: 输入图像
            marker_positions: 标记物理位置 {marker_id: (x_mm, y_mm)}

        Returns:
            仿射变换矩阵（3x3）
        """
        # 检测标记
        corners, ids = self.detect_markers(image)

        if len(ids) < 3:
            print("错误: 需要至少3个标记来计算变换矩阵")
            return None

        # 收集匹配的点对
        src_points = []  # 图像坐标
        dst_points = []  # 物理坐标

        for i, marker_id in enumerate(ids):
            marker_id = int(marker_id)

            # 跳过未知标记
            if marker_id not in marker_positions:
                continue

            # 获取标记中心点（图像坐标）
            corner = corners[i][0]
            center_x = np.mean(corner[:, 0])
            center_y = np.mean(corner[:, 1])

            # 获取物理坐标
            phys_x, phys_y = marker_positions[marker_id]

            src_points.append([center_x, center_y])
            dst_points.append([phys_x, phys_y])

        if len(src_points) < 3:
            print("错误: 匹配的标记数量不足")
            return None

        src_points = np.array(src_points, dtype=np.float32)
        dst_points = np.array(dst_points, dtype=np.float32)

        # 计算仿射变换矩阵
        self.transformation_matrix = cv2.getAffineTransform(src_points[:3], dst_points[:3])

        print("✓ 变换矩阵计算成功")
        return self.transformation_matrix

    def image_to_physical(self, image_point: Tuple[float, float]) -> Tuple[float, float]:
        """
        将图像坐标转换为物理坐标

        Args:
            image_point: 图像坐标 (x, y)

        Returns:
            物理坐标 (x_mm, y_mm)
        """
        if self.transformation_matrix is None:
            raise ValueError("变换矩阵未计算，请先调用 calculate_transformation_matrix")

        # 转换为齐次坐标
        point = np.array([image_point[0], image_point[1], 1], dtype=np.float32)

        # 应用变换
        physical_point = self.transformation_matrix @ point

        return (physical_point[0], physical_point[1])

    def physical_to_image(self, physical_point: Tuple[float, float]) -> Tuple[float, float]:
        """
        将物理坐标转换为图像坐标

        Args:
            physical_point: 物理坐标 (x_mm, y_mm)

        Returns:
            图像坐标 (x, y)
        """
        if self.transformation_matrix is None:
            raise ValueError("变换矩阵未计算，请先调用 calculate_transformation_matrix")

        # 计算逆变换
        inv_matrix = cv2.invertAffineTransform(self.transformation_matrix)

        # 转换为齐次坐标
        point = np.array([physical_point[0], physical_point[1], 1], dtype=np.float32)

        # 应用逆变换
        image_point = inv_matrix @ point

        return (image_point[0], image_point[1])

    def save_calibration(self, save_path: str):
        """
        保存校准数据

        Args:
            save_path: 保存路径
        """
        calibration_data = {
            'transformation_matrix': self.transformation_matrix,
            'work_area_width': self.work_area_width,
            'work_area_height': self.work_area_height,
            'marker_size': self.marker_size
        }

        with open(save_path, 'wb') as f:
            pickle.dump(calibration_data, f)

        print(f"✓ 校准数据已保存到: {save_path}")

    def load_calibration(self, load_path: str):
        """
        加载校准数据

        Args:
            load_path: 加载路径
        """
        with open(load_path, 'rb') as f:
            calibration_data = pickle.load(f)

        self.transformation_matrix = calibration_data['transformation_matrix']
        self.work_area_width = calibration_data['work_area_width']
        self.work_area_height = calibration_data['work_area_height']
        self.marker_size = calibration_data['marker_size']

        print(f"✓ 校准数据已从 {load_path} 加载")

    def calibrate_from_image(
        self,
        image_path: str,
        marker_positions: dict,
        save_path: Optional[str] = None
    ) -> bool:
        """
        从图像进行校准

        Args:
            image_path: 图像路径
            marker_positions: 标记物理位置 {marker_id: (x_mm, y_mm)}
            save_path: 校准数据保存路径（可选）

        Returns:
            是否成功
        """
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"错误: 无法读取图像 {image_path}")
            return False

        # 图像矫正
        print("正在矫正图像...")
        unwarp_image = self.unwarper.unwarp_image(image)

        # 检测标记并计算变换矩阵
        print("正在检测ArUco标记...")
        self.calculate_transformation_matrix(unwarp_image, marker_positions)

        # 保存校准数据
        if save_path and self.transformation_matrix is not None:
            self.save_calibration(save_path)

        return self.transformation_matrix is not None

    def generate_markers_gcode(
        self,
        marker_positions: dict,
        marker_size_mm: float = 30.0,
        gcode_path: Optional[str] = None,
        preview_path: Optional[str] = None
    ) -> Optional[str]:
        """
        生成绘制ArUco标记的Gcode

        Args:
            marker_positions: 标记物理位置 {marker_id: (x_mm, y_mm)}
            marker_size_mm: 标记物理尺寸（毫米）
            gcode_path: Gcode保存路径（可选）
            preview_path: 预览图保存路径（可选）

        Returns:
            Gcode字符串，如果失败返回None
        """
        try:
            # 生成ArUco标记图像
            generator = ArUcoMarkerGenerator(marker_size=int(marker_size_mm * 10))  # 像素大小 = 物理尺寸 * 10

            # 创建预览画布（物理坐标系）
            work_width = int(self.work_area_width)
            work_height = int(self.work_area_height)
            preview_image = np.ones((work_height, work_width), dtype=np.uint8) * 255

            # 生成Gcode
            gcode_lines = []
            gcode_lines.append("; Auto-generated ArUco markers for calibration")
            gcode_lines.append("G21 ; Set units to millimeters")
            gcode_lines.append("G90 ; Use absolute coordinates")
            gcode_lines.append("G1 Z5.0 F3000 ; Lift pen")
            gcode_lines.append("")

            for marker_id, (x_mm, y_mm) in marker_positions.items():
                print(f"正在生成标记 {marker_id} 的绘制指令...")

                # 生成单个标记
                marker_img = generator.generate_marker(int(marker_id))

                # 将标记转换为笔画路径
                strokes = self._marker_to_strokes(marker_img, x_mm, y_mm, marker_size_mm)

                # 在预览图上绘制标记
                if preview_path:
                    self._draw_marker_on_preview(preview_image, marker_img, x_mm, y_mm, marker_size_mm)

                # 添加绘制指令
                for stroke in strokes:
                    if len(stroke) < 2:
                        continue

                    # 移动到起点
                    gcode_lines.append(f"G0 X{stroke[0][0]:.3f} Y{stroke[0][1]:.3f}")
                    # 下笔
                    gcode_lines.append("G1 Z0.0 F3000")

                    # 绘制路径
                    for point in stroke[1:]:
                        gcode_lines.append(f"G1 X{point[0]:.3f} Y{point[1]:.3f} F3000")

                    # 抬笔
                    gcode_lines.append("G1 Z5.0 F3000")

                gcode_lines.append("")

            # 添加尾部
            gcode_lines.append("G1 Z5.0 ; Lift pen")
            gcode_lines.append("G0 X0 Y0 ; Return to origin")
            gcode_lines.append("M2 ; End of program")

            gcode = '\n'.join(gcode_lines)

            # 保存Gcode
            if gcode_path:
                with open(gcode_path, 'w', encoding='utf-8') as f:
                    f.write(gcode)
                print(f"✓ Gcode已保存到: {gcode_path}")

            # 保存预览图
            if preview_path:
                cv2.imwrite(preview_path, preview_image)
                print(f"✓ 预览图已保存到: {preview_path}")

            return gcode

        except Exception as e:
            print(f"生成标记Gcode失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _marker_to_strokes(
        self,
        marker_img: np.ndarray,
        x_mm: float,
        y_mm: float,
        marker_size_mm: float
    ) -> List[List[Tuple[float, float]]]:
        """
        将ArUco标记图像转换为笔画路径

        Args:
            marker_img: 标记图像（二值图）
            x_mm: 标记中心X坐标（毫米）
            y_mm: 标记中心Y坐标（毫米）
            marker_size_mm: 标记物理尺寸（毫米）

        Returns:
            笔画列表，每个笔画是一系列点
        """
        strokes = []

        # 确保是二值图
        if len(marker_img.shape) == 3:
            gray = cv2.cvtColor(marker_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = marker_img.copy()

        # 二值化（0=黑色，255=白色）
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # 标记大小（像素）
        marker_size_px = marker_img.shape[0]

        # 计算每个像素的物理尺寸
        px_to_mm = marker_size_mm / marker_size_px

        # 计算左上角坐标（标记的中心坐标减去一半尺寸）
        x_start = x_mm - marker_size_mm / 2
        y_start = y_mm - marker_size_mm / 2

        # 简单扫描：使用轮廓检测提取黑色区域的边界
        contours, _ = cv2.findContours(255 - binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # 过滤太小的轮廓
            if cv2.contourArea(contour) < 10:
                continue

            # 将轮廓坐标转换为物理坐标
            stroke = []
            for point in contour:
                px_x, px_y = point[0]

                # 转换为物理坐标（Y轴翻转）
                phys_x = x_start + px_x * px_to_mm
                phys_y = y_start + (marker_size_px - px_y) * px_to_mm

                stroke.append((phys_x, phys_y))

            if len(stroke) > 1:
                strokes.append(stroke)

        return strokes

    def _draw_marker_on_preview(
        self,
        preview_image: np.ndarray,
        marker_img: np.ndarray,
        x_mm: float,
        y_mm: float,
        marker_size_mm: float
    ):
        """
        在预览图上绘制标记

        Args:
            preview_image: 预览图像
            marker_img: 标记图像
            x_mm: 标记中心X坐标
            y_mm: 标记中心Y坐标
            marker_size_mm: 标记物理尺寸
        """
        # 计算左上角坐标
        x_start = int(x_mm - marker_size_mm / 2)
        y_start = int(y_mm - marker_size_mm / 2)
        marker_size_px = int(marker_size_mm)

        # 确保坐标在有效范围内
        if x_start < 0 or y_start < 0 or \
           x_start + marker_size_px > preview_image.shape[1] or \
           y_start + marker_size_px > preview_image.shape[0]:
            print(f"警告: 标记位置超出预览图范围 ({x_mm}, {y_mm})")
            return

        # 调整标记大小
        if marker_img.shape[0] != marker_size_px:
            marker_img = cv2.resize(marker_img, (marker_size_px, marker_size_px))

        # 确保是二值图
        if len(marker_img.shape) == 3:
            gray = cv2.cvtColor(marker_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = marker_img.copy()

        # 放置标记（翻转Y轴）
        y_end = y_start + marker_size_px
        preview_image[y_start:y_end, x_start:x_start + marker_size_px] = \
            cv2.flip(gray, 0)


def main():
    """测试函数"""
    print("=" * 70)
    print("校准模块测试")
    print("=" * 70)

    # 1. 生成ArUco标记
    print("\n1. 生成ArUco标记...")
    generator = ArUcoMarkerGenerator(marker_size=200)

    # 生成单个标记（用于测试）
    marker_img = generator.generate_marker(0, "aruco_marker_0.png")
    print("✓ 已生成标记: aruco_marker_0.png")

    # 生成标记板（用于实际校准）
    # 假设使用4个标记，放置在工作区的四个角落
    marker_ids = [0, 1, 2, 3]
    board_img = generator.generate_marker_board(marker_ids, "aruco_board.png")
    print("✓ 已生成标记板: aruco_board.png")

    # 2. 测试校准器
    print("\n2. 测试校准器...")
    calibrator = Calibrator(marker_size=30.0)

    # 定义标记的物理位置（假设4个标记在工作区的四个角落）
    # 这需要根据实际情况测量
    marker_positions = {
        0: (10, 10),      # 左上角（毫米）
        1: (207, 10),     # 右上角（毫米）
        2: (207, 289),    # 右下角（毫米）
        3: (10, 289)      # 左下角（毫米）
    }

    print("\n使用说明：")
    print("1. 打印 aruco_board.png")
    print("2. 将标记板固定在写字机工作区")
    print("3. 测量每个标记的实际物理位置")
    print("4. 拍摄写字机照片（确保标记可见）")
    print("5. 运行以下代码进行校准：")
    print("""
    # 从图像校准
    calibrator.calibrate_from_image(
        "照片路径.jpg",
        marker_positions={
            0: (x1, y1),  # 标记0的物理位置（毫米）
            1: (x2, y2),  # 标记1的物理位置
            2: (x3, y3),  # 标记2的物理位置
            3: (x4, y4),  # 标记3的物理位置
        },
        save_path="calibration.pkl"
    )

    # 使用校准数据
    # 图像坐标 -> 物理坐标
    phys_x, phys_y = calibrator.image_to_physical((100, 200))

    # 物理坐标 -> 图像坐标
    img_x, img_y = calibrator.physical_to_image((50.0, 100.0))
    """)

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
