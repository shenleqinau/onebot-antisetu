# 色图检测机器人

本项目是一个基于 Python 的 QQ 群聊图片内容检测机器人，支持自动检测群聊中的图片内容，识别色情、涉政等违规图片，并可根据配置自动撤回违规消息、保存违规图片。适用于 NapCat 框架。

---

## 功能简介

- **图片内容检测**：自动检测群聊中的图片内容，支持自定义检测标签和阈值。
- **违规内容识别**：可自定义违规关键词（如 porn、sex、politic、敏感、色情等）。
- **自动撤回**：支持为指定群聊开启自动撤回违规图片消息。
- **违规图片保存**：检测到违规图片时自动保存到本地指定目录。
- **管理员指令**：支持在群聊内通过指令管理白名单和自动撤回功能。
- **多标签中文输出**：检测结果自动翻译为中文，未翻译标签自动标注。

---

## 快速开始

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

2. **配置 `config.json`**

   - 配置 NapCat 相关参数、管理员 QQ、白名单群、自动撤回群、违规关键词、违规图片保存路径等。
   - 示例见本项目自带的 `config.json`。

3. **运行机器人**

   ```bash
   python main.py
   ```

---

## 管理员可用指令

| 指令             | 作用说明                                 |
|------------------|------------------------------------------|
| 添加检测白名单   | 将当前群聊加入图片检测白名单              |
| 移除检测白名单   | 将当前群聊从图片检测白名单移除            |
| 查看白名单       | 查看所有已加入检测白名单的群聊            |
| 开启自动撤回     | 将当前群聊加入自动撤回违规消息白名单      |

> 仅管理员可用，直接在群聊中发送即可。

---

## 配置说明

- **napcat_ws_url / napcat_http_url**：NapCat 服务的 WebSocket 和 HTTP 地址。
- **admin_qq_list**：管理员 QQ 列表。
- **whitelist_groups**：需要检测图片的群聊列表。
- **auto_recall_groups**：开启自动撤回的群聊列表。
- **violation_keywords**：违规关键词列表，可自定义。
- **violation_save_path**：违规图片保存目录。
- **model_config**：模型相关配置（版本、标签、阈值等）。

---

## 依赖

- Python 3.7+
- websockets
- aiohttp
- Pillow
- numpy
- [SensitiveImgDetect](https://github.com/W1412X/SensitiveImgDetect)

---

## 目录结构

```
.
├── main.py                # 主程序
├── image_detector.py      # 图片检测模块
├── config.json            # 配置文件
├── requirements.txt       # 依赖列表
├── violations/            # 违规图片保存目录（可自定义）
└── ...
```

---

## 贡献与反馈

如有建议或问题，欢迎提交 issue 或 PR！

---
