# EC2 Docker 部署

## 一次性准备（在 EC2 上）

1. 安装 Docker 与 Compose 插件（见项目根 README 或官方文档）。
2. 将本仓库放到部署目录，例如 `/opt/ai-assistant-deploy`（与 GitHub Secret `EC2_DEPLOY_PATH` 一致）。

## 生成密钥并启动

在服务器上，于**仓库根目录**执行：

```bash
cd /path/to/ai-assistant/deploy
chmod +x generate-env.sh docker-entrypoint.sh
./generate-env.sh
docker compose up -d --build
```

- `generate-env.sh` 会写入 `deploy/.env`（含随机 `POSTGRES_PASSWORD`、`REDIS_PASSWORD` 与 `ADMIN_PASSWORD`）。该文件已在 `.gitignore` 中，勿提交。
- 若 `.env` 已存在，脚本会跳过；需重写时：`FORCE_REGENERATE=1 ./generate-env.sh`。
- 首次初始化后默认管理员：`admin`，密码为 `.env` 中的 `ADMIN_PASSWORD`（仅首次创建时生效；若 admin 已存在则不会改密）。

## 验证

```bash
docker compose ps
docker compose logs -f --tail=100 api
curl -s http://127.0.0.1/health
```

- **Nginx** 监听宿主机 **`HTTP_PORT`（默认 80）**，反代到容器内 **api:8000**；API 不再默认映射到宿主机 8000，避免与 Nginx 混淆。
- 对外需在安全组开放 **`HTTP_PORT`**（默认 80）。HTTPS 可在 Nginx 前加 ALB 或自行挂证书。

## 常见问题

- **`api` 一直 `starting` 或 `unhealthy`**：`docker compose logs api`。常见原因：数据库未就绪、镜像构建失败、`init_db` 异常。
- **Nginx 不启动**：旧版 compose 曾要求 `api` **healthy** 后才起 Nginx；若 `api` 健康检查失败（例如镜像里没有 `curl`），Nginx 会一直不出现。当前已改为 **`api` 一起动就起 Nginx**；若 API 仍在初始化，短时间访问可能出现 **502**，属正常现象。
- **只有 `postgres` / `redis` 镜像、没有 `ai-assistant-api`**：在 `deploy` 目录执行 `docker compose build api` 或 `docker compose up -d --build`，并确认 CI 里 `docker compose` 已成功跑完。
- **镜像名**：API 镜像默认为 **`ai-assistant-api:latest`**（可在 `.env` 中设置 `API_IMAGE_NAME` / `API_IMAGE_TAG`）。

## GitHub Actions

推送 `main` 时可用 `.github/workflows/deploy-ec2.yml`（需配置 Secrets：`EC2_HOST`、`EC2_USER`、`EC2_DEPLOY_PATH`、用于 SSH 的私钥 `SETTIMO_AI`）。
