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
curl -s http://127.0.0.1:8000/health
```

对外访问需在安全组开放 `API_PORT`（默认 8000），生产环境建议前面加 Nginx/ALB 并配置 TLS。

## GitHub Actions

推送 `main` 时可用 `.github/workflows/deploy-ec2.yml`（需配置 Secrets：`EC2_HOST`、`EC2_USER`、`EC2_DEPLOY_PATH`、用于 SSH 的私钥 `SETTIMO_AI`）。
