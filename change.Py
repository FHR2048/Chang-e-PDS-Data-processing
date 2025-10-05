#嫦娥探月数据(PDS)处理与可视化
# 导入PDS4文件读取工具 - 用于读取嫦娥探月工程的科学数据格式
from pds4_tools import pds4_read
# 导入matplotlib绘图库 - 用于显示图像和直方图
import matplotlib.pyplot as plt
import matplotlib
# Jupyter notebook魔法命令 - 在notebook中内嵌显示图表
%matplotlib inline

# 导入数值计算库 - 用于数组操作和数学运算
import numpy as np
# 导入PIL图像处理库 - 用于保存处理后的图像
from PIL import Image

# 导入scikit-image图像处理模块
from skimage import exposure  # 图像对比度调整
from skimage import data, img_as_float  # 图像数据工具和浮点数转换
# 导入颜色科学库 - 用于颜色空间转换和颜色处理
import colour

# 从colour-demosaicing库导入多种去马赛克算法
from colour_demosaicing import (
    demosaicing_CFA_Bayer_bilinear,     # 双线性插值算法（基础方法）
    demosaicing_CFA_Bayer_Malvar2004,   # Malvar2004改进算法
    demosaicing_CFA_Bayer_Menon2007,    # Menon2007算法（边缘保持较好）
    mosaicing_CFA_Bayer)                # 马赛克生成工具

# 设置色彩转换函数 - 用于Gamma校正等色彩空间转换
cctf_encoding = colour.cctf_encoding
# 过滤colour库的警告信息 - 保持输出整洁
_ = colour.utilities.filter_warnings()

def read_pds(path):
    """读取PDS4格式文件并转换为浮点型图像数组
    
    参数:
        path (str): PDS4文件路径，通常是.2BL或.2CL文件
        
    返回:
        numpy.ndarray: 归一化到[0,1]范围的浮点型图像数组
    """
    # 读取PDS文件，quiet=True表示不显示读取进度信息
    data = pds4_read(path, quiet=True)
    # 提取科学数据并转换为numpy数组
    img = np.array(data[0].data)
    # 将图像数据转换为[0,1]范围的浮点数，便于后续处理
    img = img_as_float(img)
    return img

def plot_img_and_hist(image, hist=True, bins=128):
    """绘制图像及其RGB通道直方图
    
    参数:
        image (numpy.ndarray): 输入图像，RGB三通道格式
        hist (bool): 是否显示直方图，默认为True
        bins (int): 直方图的分箱数量，默认为128
    """
    if hist:
        # 创建包含图像和直方图的子图布局，高度比例为3:1
        fig, axes = plt.subplots(2, 1, figsize=(10, 10), 
                                gridspec_kw={'height_ratios': [3, 1]})
        ax_img, ax_hist = axes  # 分别获取图像轴和直方图轴
    else:
        # 仅创建图像显示区域
        fig, ax_img = plt.subplots(figsize=(10, 10))

    # 显示图像（使用灰度色彩映射）
    ax_img.imshow(image, cmap='gray')
    ax_img.set_axis_off()  # 隐藏坐标轴

    if hist:
        # 分别绘制RGB三个通道的直方图
        # ravel()将多维数组展平为一维，histtype='step'创建轮廓式直方图
        ax_hist.hist(image[:,:,0].ravel(), bins=bins, histtype='step', color='red', label='Red')
        ax_hist.hist(image[:,:,1].ravel(), bins=bins, histtype='step', color='green', label='Green')
        ax_hist.hist(image[:,:,2].ravel(), bins=bins, histtype='step', color='blue', label='Blue')

        # 设置y轴为科学计数法显示，避免大数字显示混乱
        ax_hist.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
        ax_hist.set_xlabel('Pixel intensity')  # 设置x轴标签
        ax_hist.set_xlim(0, 1)  # 设置x轴范围[0,1]
        ax_hist.set_yticks([])  # 隐藏y轴刻度
        ax_hist.legend()  # 显示图例

def export_img(name, img):
    """将浮点图像保存为8位PNG文件
    
    参数:
        name (str): 输出文件名
        img (numpy.ndarray): 浮点型图像数组，值范围[0,1]
    """
    # 将[0,1]范围的浮点数转换为[0,255]范围的8位无符号整数
    pil_img = Image.fromarray(np.uint8(img * 255))
    # 保存图像
    pil_img.save(name)

def debayer_img(img, CFA='RGGB'):
    """对Bayer格式的RAW图像进行去马赛克处理
    
    参数:
        img (numpy.ndarray): 原始Bayer格式图像
        CFA (str): Bayer滤镜阵列模式，默认为'RGGB'
        
    返回:
        numpy.ndarray: 去马赛克后的RGB图像
    """
    # 使用Menon2007算法进行去马赛克，该算法在边缘保持方面优于双线性插值
    debayered = demosaicing_CFA_Bayer_Menon2007(img, CFA)
    # 应用色彩转换函数（通常包括Gamma校正）
    debayered = cctf_encoding(debayered)
    return debayered

def stretch_img(img):
    """基于百分位的对比度拉伸
    
    参数:
        img (numpy.ndarray): 输入图像
        
    返回:
        numpy.ndarray: 对比度拉伸后的图像
    """
    # 计算图像2%和98%百分位的像素值，排除极端值
    p2, p98 = np.percentile(img, (2, 98))
    # 将图像强度重新缩放到[p2, p98]范围，增强对比度
    img = exposure.rescale_intensity(img, in_range=(p2, p98))
    return img

# 主程序执行流程
# 设置PDS文件路径 - 这里使用的是嫦娥五号PCAM相机数据
path = './CE5-L_GRAS_LCAM-1-0010_SCI_N_20201201150302_20201201150302_0001_A.2AL'

# 数据预处理流水线:
# 1. 读取PDS文件
img = read_pds(path)
# 打印图像形状，确认数据维度
print(img.shape)

# 2. 去马赛克处理 - 将Bayer格式转换为RGB
debayered = debayer_img(img)

# 3. 对比度拉伸 - 增强图像视觉效果
final = stretch_img(debayered)

# 4. 显示结果 - 图像和直方图
plot_img_and_hist(final, hist=True)
plt.show()

# 5. 保存处理后的图像
export_img(f"{path}.png", final)
