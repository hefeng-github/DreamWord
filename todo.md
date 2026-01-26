# todo

## 概览

本项目的总目标是自动查单词机和智能写字机，软件部分使用python，硬件使用[开源项目](https://oshwhub.com/supercaii/coerxy-jie-gou-xie-zi-ji-ji-guang-diao-ke-ji-_-wu-jie-3)，你需要自己选择效果最佳的实现方式，参考提到网址中的文档，配置环境，实现功能

## 可能用到的数据

- 使用Fluid NC固件
- 有效行程为217mm(x)，299mm(y)
- 中文字体使用Fonts/FZZJ-DLHTJW.TTF,英文及音标字体使用Fonts/NotoSansMath-Regular.ttf

## 目标

流程大致如下

### 查单词模块

	该模块已基本完成(word_lookup.py)

### 校准模块

1. 生成可打印的ArUco 标记(可复用，已有则跳过)
2. 输入写字机照片(有ArUco 标记)
3. 裁剪(使用[paddleocr文本图像矫正模块](https://www.paddleocr.ai/latest/version3.x/module_usage/text_image_unwarping.html) )
4. 校准(使用[ArUco 标记检测](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html) ，仿射变换)

### 写字模块

1. 校准
2. 生成可打印的ArUco 标记(可复用，已有则跳过)
3. 输入写字机照片(有ArUco 标记)
4. 裁剪(使用[paddleocr文本图像矫正模块](https://www.paddleocr.ai/latest/version3.x/module_usage/text_image_unwarping.html) )
5. 校准(使用[ArUco 标记检测](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html) ，仿射变换)
6. 输入文字
7. 对中文使用[handright项目](https://github.com/Gsllchb/Handright)
8. 渲染文字
9. 将文字位图转化为骨架图，再将骨架图转化为笔画图，再将笔画图转化为控制写字机的Gcode
10. 控制写字机

### 自动查单词模块

1. 输入试卷在写字机上的图片
2. 裁剪(使用[paddleocr文本图像矫正模块](https://www.paddleocr.ai/latest/version3.x/module_usage/text_image_unwarping.html) )
3. ocr，获取文字坐标(使用[PP-OCRv5](https://www.paddleocr.ai/latest/version3.x/pipeline_usage/OCR.html) )
4. 将ocr获取的单词与已会单词(SQLite数据库)比对，取不会的单词
5. 查单词(使用word_lookup.py)，取最合适释义中的第一个词语，返回的第一个音标
6. 寻找可书写行间区域，确定释义和音标的书写位置
7. 若有可能重叠的书写，把书写位置向两边移动直到不再重合
8. 把书写数据传至写字模块进行书写

### 自动抄写模块

1. 输入空白横线本在写字机上的图片和要抄写的文字
2. 裁剪(使用[paddleocr文本图像矫正模块](https://www.paddleocr.ai/latest/version3.x/module_usage/text_image_unwarping.html) )
3. 识别横线及可写区域(横线之间)
4. 排版文字，传入写字模块进行书写
