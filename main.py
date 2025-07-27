import asyncio
import websockets
import json
import logging
import aiohttp
import base64
import os
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from image_detector import ImageDetector

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 设置为DEBUG级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        # 新增自动撤回白名单
        if "auto_recall_groups" not in self.config:
            self.config["auto_recall_groups"] = []
            self.save_config()
        # 新增违规图片保存路径
        if "violation_save_path" not in self.config:
            self.config["violation_save_path"] = "violations"
            self.save_config()

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "napcat_ws_url": "ws://localhost:3001",
            "napcat_http_url": "http://localhost:3000",
            "admin_qq_list": [],
            "whitelist_groups": [],
            "bot_qq": "",
            "model_config": {
                "version": "v2",
                "labels": ["cartoon", "porn", "politic", "other"],
                "confidence_threshold": 0.65
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return default_config
        else:
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """保存配置文件"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.config = config
            logger.info("配置文件已保存")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def add_whitelist_group(self, group_id: str) -> bool:
        """添加白名单群组"""
        if group_id not in self.config['whitelist_groups']:
            self.config['whitelist_groups'].append(group_id)
            self.save_config()
            return True
        return False
    
    def remove_whitelist_group(self, group_id: str) -> bool:
        """移除白名单群组"""
        if group_id in self.config['whitelist_groups']:
            self.config['whitelist_groups'].remove(group_id)
            self.save_config()
            return True
        return False
    
    def is_admin(self, qq: str) -> bool:
        """检查是否为管理员"""
        return qq in self.config['admin_qq_list']
    
    def is_whitelist_group(self, group_id: str) -> bool:
        """检查是否为白名单群组"""
        return group_id in self.config['whitelist_groups']

    def add_auto_recall_group(self, group_id: str) -> bool:
        """添加自动撤回白名单群组"""
        if group_id not in self.config['auto_recall_groups']:
            self.config['auto_recall_groups'].append(group_id)
            self.save_config()
            return True
        return False

    def is_auto_recall_group(self, group_id: str) -> bool:
        """检查是否为自动撤回白名单群组"""
        return group_id in self.config['auto_recall_groups']

class NapCatBot:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.image_detector = ImageDetector(self.config_manager.config)
        self.websocket = None
        self.running = False
        self.label_map = {
            "cartoon": "动漫",
            "carton": "动漫",
            "porn": "色情",
            "politic": "涉政",
            "other": "其他",
            "explicit": "露骨",
            "sexual": "性暗示",
            "sex": "性相关",
            "敏感": "敏感",
            "色情": "色情"
        }
        self.violation_keywords = self.config_manager.config.get(
            "violation_keywords",
            ["porn", "politic", "explicit", "sexual", "sex", "敏感", "色情"]
        )
        # 违规图片保存路径
        self.violation_save_path = self.config_manager.config.get("violation_save_path", "violations")
        os.makedirs(self.violation_save_path, exist_ok=True)

    async def connect(self):
        """连接到NapCat WebSocket"""
        ws_url = self.config_manager.config['napcat_ws_url']
        try:
            self.websocket = await websockets.connect(ws_url)
            self.running = True
            logger.info(f"已连接到NapCat: {ws_url}")
            return True
        except Exception as e:
            logger.error(f"连接NapCat失败: {e}")
            return False
    
    async def send_message(self, message_type: str, target_id: str, message: str):
        """发送消息"""
        try:
            http_url = self.config_manager.config['napcat_http_url']
            
            if message_type == 'group':
                url = f"{http_url}/send_group_msg"
                data = {
                    "group_id": int(target_id),
                    "message": message
                }
            elif message_type == 'private':
                url = f"{http_url}/send_private_msg"
                data = {
                    "user_id": int(target_id),
                    "message": message
                }
            else:
                logger.error(f"不支持的消息类型: {message_type}")
                return
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"消息发送成功: {message}")
                    else:
                        logger.error(f"消息发送失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """下载图片"""
        try:
            logger.debug(f"开始下载图片: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        logger.debug(f"图片下载成功，大小: {len(image_data)} 字节")
                        return image_data
                    else:
                        logger.error(f"下载图片失败: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"下载图片异常: {e}")
            return None
    
    async def process_image_message(self, group_id: str, user_id: str, message_data: List[Dict], message_id: Optional[int] = None):
        """处理图片消息"""
        try:
            logger.debug(f"收到图片消息，群组: {group_id}, 用户: {user_id}")
            for segment in message_data:
                if segment.get('type') == 'image':
                    image_url = segment.get('data', {}).get('url')
                    if not image_url:
                        logger.warning("图片消息中没有URL")
                        continue
                    
                    logger.debug(f"发现图片URL: {image_url}")
                    # 下载图片
                    image_data = await self.download_image(image_url)
                    if not image_data:
                        logger.warning("图片下载失败，跳过处理")
                        continue
                    
                    # 调用图片检测模块
                    logger.debug("开始检测图片内容")
                    results = await self.image_detector.detect_image(image_data)
                    logger.debug(f"检测完成，结果数量: {len(results)}")
                    
                    if results:
                        # 处理检测结果，传递 message_id 和 image_data
                        await self.handle_detection_results(group_id, user_id, results, message_id, image_data=image_data, image_url=image_url)
                    else:
                        logger.warning("未获得检测结果")
                        
        except Exception as e:
            logger.error(f"处理图片消息异常: {e}", exc_info=True)

    async def recall_message(self, message_id: int):
        """撤回消息"""
        try:
            http_url = self.config_manager.config['napcat_http_url']
            url = f"{http_url}/delete_msg"
            data = {"message_id": message_id}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"消息撤回成功: {message_id}")
                    else:
                        logger.error(f"消息撤回失败: {response.status}")
        except Exception as e:
            logger.error(f"撤回消息异常: {e}")

    async def handle_detection_results(self, group_id: str, user_id: str, results: List[Dict], message_id: Optional[int] = None, image_data: Optional[bytes] = None, image_url: Optional[str] = None):
        """处理检测结果"""
        if not results:
            logger.warning("没有检测到任何结果")
            return
        
        logger.debug(f"检测结果: {json.dumps(results, ensure_ascii=False, indent=2)}")
        
        violation_found = False
        result_text = "🔍 图片检测结果:\n"
        violation_labels = []

        for i, result in enumerate(results, 1):
            label = result.get('label', '未知')
            label_cn = self.label_map.get(label.lower(), f"{label}(未翻译)")
            confidence = result.get('confidence', 0)
            result_text += f"{i}. {label_cn}: {confidence:.2%}\n"
            
            if confidence > self.image_detector.confidence_threshold:
                if any(keyword in label.lower() for keyword in self.violation_keywords):
                    violation_found = True
                    violation_labels.append(label_cn)
                    logger.info(f"检测到违规内容: {label_cn} ({confidence:.2%})")
        
        # 检测到违规内容时保存图片
        if violation_found and image_data:
            try:
                now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                label_str = "_".join(violation_labels) if violation_labels else "violation"
                filename = f"{now}_群{group_id}_用户{user_id}_{label_str}.jpg"
                save_path = os.path.join(self.violation_save_path, filename)
                with open(save_path, "wb") as f:
                    f.write(image_data)
                logger.info(f"违规图片已保存到: {save_path}")
            except Exception as e:
                logger.error(f"保存违规图片失败: {e}")

        if violation_found:
            warning_msg = f"⚠️ 检测到可能的违规内容!\n{result_text}\n请注意群规，维护良好的聊天环境。"
            await self.send_message('group', group_id, warning_msg)
            logger.info("已发送违规警告")
            # 自动撤回功能
            if self.config_manager.is_auto_recall_group(group_id) and message_id:
                await self.recall_message(message_id)
        else:
            logger.info("未检测到违规内容")
            # 可选：发送正常结果
            # info_msg = f"图片检测结果:\n{result_text}"
            # await self.send_message('group', group_id, info_msg)
    
    async def handle_admin_command(self, user_id: str, group_id: str, message: str):
        """处理管理员命令"""
        if not self.config_manager.is_admin(user_id):
            logger.debug(f"用户 {user_id} 不是管理员，忽略命令")
            return
        
        message = message.strip()
        logger.debug(f"处理管理员命令: {message}")
        
        if message == "添加检测白名单":
            if self.config_manager.add_whitelist_group(group_id):
                await self.send_message('group', group_id, "✅ 当前群聊已添加到图片检测白名单")
            else:
                await self.send_message('group', group_id, "ℹ️ 当前群聊已在白名单中")
        elif message == "开启自动撤回":
            if self.config_manager.add_auto_recall_group(group_id):
                await self.send_message('group', group_id, "✅ 当前群聊已开启自动撤回违规消息")
            else:
                await self.send_message('group', group_id, "ℹ️ 当前群聊已开启自动撤回")
        elif message == "移除检测白名单":
            if self.config_manager.remove_whitelist_group(group_id):
                await self.send_message('group', group_id, "✅ 当前群聊已从图片检测白名单移除")
            else:
                await self.send_message('group', group_id, "ℹ️ 当前群聊不在白名单中")
        elif message == "查看白名单":
            whitelist = self.config_manager.config['whitelist_groups']
            if whitelist:
                whitelist_text = "\n".join([f"- {group}" for group in whitelist])
                await self.send_message('group', group_id, f"📋 当前白名单群聊:\n{whitelist_text}")
            else:
                await self.send_message('group', group_id, "📋 白名单为空")
    
    async def process_message(self, data: Dict[str, Any]):
        """处理收到的消息"""
        try:
            post_type = data.get('post_type')
            if post_type != 'message':
                return
            
            message_type = data.get('message_type')
            if message_type != 'group':
                return
            
            group_id = str(data.get('group_id', ''))
            user_id = str(data.get('user_id', ''))
            message = data.get('message', [])
            message_id = data.get('message_id', None)
            
            logger.debug(f"收到群消息: 群号={group_id}, 用户={user_id}")
            
            # 如果不是白名单群组，检查是否为管理员命令
            if not self.config_manager.is_whitelist_group(group_id):
                logger.debug(f"群组 {group_id} 不在白名单中")
                if self.config_manager.is_admin(user_id):
                    # 提取文本消息
                    text_message = ""
                    for segment in message:
                        if segment.get('type') == 'text':
                            text_message += segment.get('data', {}).get('text', '')
                    
                    logger.debug(f"管理员命令: {text_message}")
                    await self.handle_admin_command(user_id, group_id, text_message)
                return
            
            logger.debug(f"群组 {group_id} 在白名单中，检查图片")
            # 白名单群组，处理图片消息
            has_image = any(segment.get('type') == 'image' for segment in message)
            if has_image:
                logger.debug("消息包含图片，开始处理")
                await self.process_image_message(group_id, user_id, message, message_id)
            else:
                logger.debug("消息不包含图片，跳过处理")
                
        except Exception as e:
            logger.error(f"处理消息异常: {e}", exc_info=True)
    
    async def listen(self):
        """监听消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    logger.debug(f"收到WebSocket消息: {message[:200]}...")
                    await self.process_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {e}")
                except Exception as e:
                    logger.error(f"处理消息异常: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
            self.running = False
        except Exception as e:
            logger.error(f"监听消息异常: {e}")
            self.running = False
    
    async def run(self):
        """运行机器人"""
        logger.info("正在启动NapCat机器人...")
        
        # 检查配置
        if not self.config_manager.config['admin_qq_list']:
            logger.error("请在config.json中配置管理员QQ")
            return
        
        while True:
            try:
                if await self.connect():
                    await self.listen()
                else:
                    logger.error("连接失败，5秒后重试...")
                    await asyncio.sleep(5)
                    
                if not self.running:
                    logger.info("5秒后尝试重连...")
                    await asyncio.sleep(5)
                    
            except KeyboardInterrupt:
                logger.info("收到退出信号，正在关闭...")
                break
            except Exception as e:
                logger.error(f"运行异常: {e}")
                await asyncio.sleep(5)
    
    async def close(self):
        """关闭连接"""
        self.running = False
        if self.websocket:
            await self.websocket.close()

async def main():
    bot = NapCatBot()
    try:
        await bot.run()
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())