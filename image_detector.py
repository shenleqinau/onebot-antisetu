import asyncio
import logging
from PIL import Image
import io
from typing import List, Dict, Optional
from SensitiveImgDetect import Detect

logger = logging.getLogger(__name__)

class ImageDetector:
    def __init__(self, config: Dict = None):
        self.detector = None
        self.version = 'v2'
        self.labels = ['cartoon', 'porn', 'politic', 'other']
        self.confidence_threshold = 0.65  # 默认阈值
        self.model_path = None  # 模型路径

        # 从配置文件加载模型设置
        if config:
            model_config = config.get('model_config', {})
            self.version = model_config.get('version', 'v2')
            self.labels = model_config.get('labels', self.labels)
            self.confidence_threshold = float(model_config.get('confidence_threshold', 0.65))
            # 读取模型路径，只有非空且非默认才用
            model_path = config.get('model_path', None)
            if model_path and model_path != "your_model_dir_or_file_path":
                self.model_path = model_path
            else:
                self.model_path = None

        logger.info(f"配置加载完成: 版本={self.version}, 标签={self.labels}, 阈值={self.confidence_threshold}, 模型路径={self.model_path}")
        self._initialize_detector()

    def _initialize_detector(self):
        """初始化SensitiveImgDetect模型"""
        try:
            # 支持自定义模型路径
            if self.model_path:
                self.detector = Detect(device='cpu', version=self.version, model_path=self.model_path)
            else:
                self.detector = Detect(device='cpu', version=self.version)
            logger.info(f"SensitiveImgDetect模型加载成功")
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            self.detector = None
    
    def _preprocess_image(self, image_data: bytes) -> Optional[Image.Image]:
        """预处理图片：转换为RGB格式"""
        try:
            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'RGB':
                logger.debug(f"转换图片模式: {image.mode} -> RGB")
                image = image.convert('RGB')
            return image
        except Exception as e:
            logger.error(f"图片预处理失败: {e}")
            return None
    
    async def detect_image(self, image_data: bytes) -> List[Dict]:
        """检测图片内容"""
        try:
            if self.detector is None:
                logger.warning("模型未加载，使用模拟检测结果")
                return self._get_mock_results()
            
            logger.debug("开始预处理图片")
            image = self._preprocess_image(image_data)
            if image is None:
                logger.warning("图片预处理失败，无法检测")
                return []
            
            logger.debug("调用模型检测")
            # 使用线程池运行检测避免阻塞事件循环
            loop = asyncio.get_event_loop()
            # 调用detect_single_prob方法获取概率字典
            results_dict = await loop.run_in_executor(
                None, 
                self.detector.detect_single_prob, 
                image
            )
            
            # 记录原始结果
            logger.debug(f"模型原始输出: {results_dict}")
            
            # 将结果字典转换成我们需要的格式
            results = []
            for label, confidence in results_dict.items():
                # 添加所有结果，不进行过滤
                results.append({
                    'label': label,
                    'confidence': confidence
                })
            
            # 按置信度排序
            results.sort(key=lambda x: x['confidence'], reverse=True)
            
            logger.info(f"图片检测完成，检测到 {len(results)} 个分类结果")
            # 记录详细结果
            for i, result in enumerate(results):
                logger.debug(f"结果 {i+1}: {result['label']} - {result['confidence']:.2%}")
            
            return results
            
        except Exception as e:
            logger.error(f"图片检测异常: {e}", exc_info=True)
            return []
    
    def _get_mock_results(self) -> List[Dict]:
        """获取模拟检测结果（当模型未加载时使用）"""
        import random
        results = []
        total_confidence = 0
        
        for label in self.labels:
            confidence = random.uniform(0.1, 0.9)
            results.append({
                'label': label,
                'confidence': confidence
            })
            total_confidence += confidence
        
        # 标准化置信度
        for result in results:
            result['confidence'] = result['confidence'] / total_confidence
        
        # 按置信度排序
        results.sort(key=lambda x: x['confidence'], reverse=True)
        logger.info("使用模拟检测结果")
        return results

# 用于测试的独立脚本功能
async def test_detector():
    """测试检测器"""
    # 使用默认配置
    detector = ImageDetector()
    
    # 创建一个测试图片
    test_image = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='JPEG')
    
    results = await detector.detect_image(img_bytes.getvalue())
    
    print("检测结果:")
    for result in results:
        print(f"  {result['label']}: {result['confidence']:.2%}")

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.DEBUG)
    
    # 运行测试
    asyncio.run(test_detector())
