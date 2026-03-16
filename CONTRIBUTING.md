# 贡献指南

感谢您对AI量化交易机器人项目的关注！

## 如何贡献

### 报告问题

如果您发现了bug或有功能建议，请通过GitHub Issues提交：

1. 检查是否已有类似问题
2. 使用问题模板创建新Issue
3. 提供详细的复现步骤

### 提交代码

1. Fork本仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

### 代码规范

- 遵循PEP 8代码风格
- 添加适当的文档字符串
- 为新功能添加测试
- 确保所有测试通过

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/crypto-trading-bot.git
cd crypto-trading-bot

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 运行测试
python -m unittest discover tests
```

## 联系方式

如有问题，欢迎通过GitHub Discussions交流。
