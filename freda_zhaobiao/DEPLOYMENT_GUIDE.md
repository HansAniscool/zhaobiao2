# 部署平台推荐与选择指南

## 1. Render (推荐)
**优点**：
- 免费层包含1个Web服务和1个PostgreSQL数据库（3个月免费）
- 支持自定义域名
- 自动SSL证书
- 直接从GitHub/GitLab部署
- 支持Python和Flask
- 每月100GB带宽

**缺点**：
- 免费服务可能会有冷启动延迟
- 数据库3个月后需要付费（但可以使用其他免费数据库）

## 2. Vercel
**优点**：
- 免费层支持无服务器函数
- 自动SSL证书
- 支持自定义域名
- 优秀的CDN性能

**缺点**：
- 主要针对静态网站，后端功能有限
- 不直接支持Flask应用

## 3. Railway
**优点**：
- 免费层包含1个Web服务和1个PostgreSQL数据库
- 支持自定义域名
- 自动SSL证书
- 直接从GitHub部署

**缺点**：
- 免费层有使用限制

## 4. Heroku
**优点**：
- 传统的PaaS平台，适合Flask应用
- 支持自定义域名
- 大量文档和社区支持

**缺点**：
- 免费层应用30分钟无访问会休眠
- 不再提供免费的Heroku Postgres

---

## 推荐选择：Render
基于你的需求（Python Flask应用、自定义域名、免费），Render是最适合的选择。

## Render部署详细步骤

### 步骤1：准备GitHub仓库

1. 将你的项目代码推送到GitHub仓库
2. 确保仓库包含以下文件：
   - `requirements.txt` - 包含所有依赖
   - `Procfile` - 定义启动命令
   - `.env.example` - 环境变量示例

### 步骤2：注册Render账号

1. 访问Render官网：https://render.com/
2. 点击「Sign Up」按钮，使用GitHub账号登录（推荐）或使用邮箱注册

### 步骤3：部署Flask应用

1. 登录后，点击仪表盘的「New +」按钮，选择「Web Service」
2. 连接你的GitHub仓库：
   - 如果你是首次使用，需要授权Render访问你的GitHub仓库
   - 选择你要部署的项目仓库
3. 配置部署设置：
   - **Name**: 为你的应用取一个名称
   - **Region**: 选择离你最近的区域（如「Oregon (US West)」）
   - **Branch**: 选择主分支（通常是`main`或`master`）
   - **Root Directory**: 保持默认（如果项目在根目录）
   - **Runtime**: 选择「Python 3」
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: 从Procfile自动获取（通常是`gunicorn app:app -b 0.0.0.0:$PORT`）

### 步骤4：配置环境变量

1. 在部署配置页面，滚动到「Environment Variables」部分
2. 点击「Add Environment Variable」，添加以下必要的环境变量：
   - `SECRET_KEY`: 一个安全的随机字符串（可使用`openssl rand -hex 32`生成）
   - `DATABASE_URL`: PostgreSQL数据库连接字符串（将在下一步创建）
   - `FLASK_ENV`: `production`
   - `DEBUG`: `False`
3. 点击「Save」保存配置

### 步骤5：创建PostgreSQL数据库

1. 返回Render仪表盘，点击「New +」按钮，选择「PostgreSQL」
2. 配置数据库：
   - **Name**: 为数据库取一个名称
   - **Region**: 选择与应用相同的区域
   - **Database**: 数据库名称（自动生成）
   - **User**: 数据库用户名（自动生成）
   - **Password**: 数据库密码（自动生成或自定义）
3. 点击「Create Database」创建数据库
4. 数据库创建成功后，在数据库详情页复制「Internal Database URL」或「External Database URL」
5. 返回应用部署页面，更新`DATABASE_URL`环境变量为刚复制的连接字符串

### 步骤6：部署应用

1. 在应用部署页面，点击「Create Web Service」按钮开始部署
2. Render将自动克隆你的仓库，安装依赖，并启动应用
3. 部署过程中，你可以在「Logs」标签页查看部署日志
4. 部署成功后，你将看到一个绿色的「Live」标签和应用的URL

### 步骤7：配置自定义域名

1. 在应用详情页，点击「Settings」标签页
2. 滚动到「Custom Domains」部分
3. 点击「Add Custom Domain」按钮，输入你的个人域名（如`yourdomain.com`或`www.yourdomain.com`）
4. Render将显示需要添加的DNS记录（通常是CNAME记录）
5. 按照Render的提示，在阿里云域名管理控制台添加相应的DNS记录（参考ALIYUN_DNS_SETUP.md）
6. DNS记录生效后，Render会自动验证域名并颁发SSL证书

### 步骤8：初始化数据库

1. 应用部署成功后，你需要初始化数据库表结构
2. 在Render仪表盘，进入应用详情页，点击「Shell」标签页
3. 在Shell中运行数据库迁移脚本：
   ```bash
   python migrate_db.py
   ```
4. 脚本将自动创建数据库表结构和初始管理员用户

## 部署后的验证

部署完成后，你可以通过以下方式验证：

1. **访问应用**：通过你的个人域名或Render提供的URL访问应用
2. **登录管理后台**：使用初始管理员账号（用户名：admin，密码：admin123）登录
3. **测试功能**：尝试使用应用的核心功能，确保一切正常

## 常见问题

### Q: 部署失败怎么办？
A: 查看部署日志，常见原因包括：
- 依赖安装失败：检查requirements.txt文件
- 环境变量配置错误：检查DATABASE_URL等关键变量
- Procfile格式错误：确保Procfile包含正确的启动命令

### Q: 如何更新部署的应用？
A: 只需将最新代码推送到GitHub仓库，Render会自动检测并重新部署。

### Q: 如何查看应用日志？
A: 在Render应用详情页，点击「Logs」标签页即可查看实时日志。

---

完成以上步骤后，你的Flask应用将成功部署在Render平台，并可以通过个人域名访问。