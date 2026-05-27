# 小米 Token Plan 配额监控

一个基于 **Vue3 + TypeScript + TailwindCSS + FastAPI** 的监控页面，用于查看 Xiaomi Mimo 平台 Token Plan 配额使用情况，支持多账号管理。

## 功能

- 多账号页面纵向展示（非切换模式）
- 账号添加 / 编辑（弹窗表单）
- 指标展示：
  - 月度积分（`plan_total_token.used`）
  - 补偿积分（`compensation_total_token.used`）
  - 总使用率
  - 总配额
- 数值单位自动缩写：`k / M / B`
- 首次加载自动刷新全部账号
- 每 5 分钟自动刷新

## 技术栈

- 前端：Vue 3 + TypeScript + Vite + TailwindCSS
- 后端：FastAPI + httpx
- 部署：Docker（单容器，Python 托管前端静态页面）
- CI/CD：GitHub Actions 自动构建并推送 GHCR 多架构镜像（amd64/arm64）

---

## 目录结构

```text
.
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── accounts.json        # 本地使用（已忽略提交/打包）
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── Dockerfile
├── .dockerignore
└── .github/workflows/docker-publish.yml
```

---

## 本地开发

### 1) Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2) 前端依赖

```bash
npm --prefix frontend install
```

### 3) 启动后端

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 4) 启动前端（开发模式）

```bash
npm --prefix frontend run dev
```

---

## Docker 一体化运行（推荐部署）

> 由 Python/FastAPI 直接托管前端构建产物，不需要单独前端服务。

### 构建镜像

```bash
docker build -t xiaomimimo-token-monitor .
```

### 拉取 GHCR 镜像

```bash
docker pull ghcr.io/w101723/xiaomimimo_token_usage_detection:latest
```

### 运行容器

```bash
docker run --rm -p 8000:8000 ghcr.io/w101723/xiaomimimo_token_usage_detection:latest
```

访问：<http://127.0.0.1:8000/>

---

## 账号配置与安全

- 账号信息通过 `backend/accounts.json` 存储（包含 cookie 等敏感字段）。
- 该文件已加入：
  - `.gitignore`
  - `.dockerignore`
- 建议通过运行时挂载方式提供账号文件：

```bash
docker run --rm -p 8000:8000 \
  -v $(pwd)/backend/accounts.json:/app/backend/accounts.json \
  xiaomimimo-token-monitor
```

---

## GitHub Actions 自动发布镜像

工作流文件：`.github/workflows/docker-publish.yml`

触发条件：

- push 到 `main`
- 手动触发（`workflow_dispatch`）

发布目标：

- GHCR：`ghcr.io/w101723/xiaomimimo_token_usage_detection`
- 平台：`linux/amd64`, `linux/arm64`
- 标签：`latest`（默认分支）和 `sha-<commit>`

---

## 常用命令

```bash
# 前端构建
npm --prefix frontend run build

# 后端语法检查
python3 -m compileall backend/main.py
```
