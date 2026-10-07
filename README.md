# Challenge Stack

一个容器解决验证码识别、分流和求解，外网走 `https://challenge.cool.pp.ua`，Caddy 自动申请并续签证书。

## 这个容器做什么

1. 看 HTML / iframe / sitekey / 脚本特征，判断是哪种挑战
2. 分流到对应后端
3. 对外只暴露一个 HTTPS API

当前能真正求解：

- Cloudflare Turnstile
- Cloudflare 5 秒盾 / managed challenge
- reCAPTCHA Invisible / v3
- 简单图片 OCR（`ImageToText`）
- 点选格子图（reCAPTCHA v2 / hCaptcha / AWS WAF / bCaptcha classification）

点选目前靠 YOLO 认物体，能解汽车、公交车、卡车、自行车、摩托车、红绿灯、消防栓、船、飞机等。楼梯、人行横道、烟囱、桥、山、棕榈树还没有开放词汇模型，会明确报错。

把格子图和题目发给 API，返回要点的序号。浏览器插件可在页面上自动点。sitekey 本身换不回 token，token 仍要页面点完后自己生成。

能识别但还不能完整拿 token：

- FunCaptcha
- 没有图的 hCaptcha / AWS WAF

## 机器要求

- x86_64 Linux + Docker
- 内存 2GB 起步，推荐 4GB
- 开放 80/443，给 Let's Encrypt 用

## 部署

```bash
cp .env.example .env
# 生成随机 key，然后填写 CLIENTT_KEY、DOMAIN、ACME_EMAIL
openssl rand -hex 32
docker compose pull
docker compose up -d
curl -s https://challenge.cool.pp.ua/health
```

域名必须先解析到这台机器。证书由 Caddy 自动续签，不用 certbot。

## Docker Hub 镜像

默认 Compose 使用已经发布的 Docker Hub 镜像：

```text
circling0635/challenge-gateway:2026.10.08
```

查看状态和日志：

```bash
docker compose ps
docker compose logs -f challenge
```

升级到新版本时先修改 `CHALLENGE_IMAGE`，再执行：

```bash
docker compose pull
docker compose up -d
```

生产环境建议使用日期版本，不要直接使用 `latest`。如果需要从当前源码重新构建，Dockerfile 仍然保留，可以执行：

```bash
docker build -t challenge-gateway:local .
```

## 配置说明

| 变量 | 是否必需 | 说明 |
| --- | --- | --- |
| `CLIENTT_KEY` | 是 | 所有受保护接口共用的随机访问 key |
| `DOMAIN` | 是 | Caddy 对外提供 HTTPS 的域名，必须解析到本机 |
| `ACME_EMAIL` | 是 | Let's Encrypt 证书通知邮箱 |
| `ENABLE_TLS` | 否 | 默认 `true`，生产环境保持开启 |
| `CLOUDFLYER_BIND` | 否 | 底层 3000 端口的绑定地址，生产环境建议 `127.0.0.1` |
| `CLOUDFLYER_MAX_TASKS` | 否 | 同时运行的底层求解任务数，默认 `1` |
| `CLOUDFLYER_TIMEOUT` | 否 | 底层任务超时时间，单位为秒 |
| `CHALLENGE_IMAGE` | 否 | Docker Hub 镜像名，默认使用固定版本 |
| `OCR_ENSEMBLE_ENABLED` | 否 | 对 EUserv 验证码启用多模型候选，默认 `true` |
| `OCR_ENSEMBLE_MAX_ALTERNATIVES` | 否 | 每张 EUserv 验证码最多返回的备选结果数，默认 `3` |

生成 key：

```bash
openssl rand -hex 32
```

同一套 key 要配置到 NodeSeek、EUserv 等调用方的 `CLIENTT_KEY` 或
`CHALLENGE_GATEWAY_KEY`。不要把真实 key 写进 GitHub、前端代码、URL 或日志。

## API

特征识别：

```http
POST /detect
{
  "url": "https://www.nodeseek.com/signIn.html",
  "html": "<div class='cf-turnstile' data-sitekey='0x4...'></div>"
}
```

Cloudflyer 兼容（NodeSeek 直接用）：

```http
POST /createTask
{
  "clientKey": "和 .env 相同",
  "type": "Turnstile",
  "url": "https://www.nodeseek.com/signIn.html",
  "siteKey": "0x4AAAAAAAaNy7leGjewpVyR"
}
```

CapSolver 兼容：

```http
POST /createTask
{
  "clientKey": "和 .env 相同",
  "task": {
    "type": "AntiTurnstileTaskProxyLess",
    "websiteURL": "https://www.nodeseek.com/signIn.html",
    "websiteKey": "0x4AAAAAAAaNy7leGjewpVyR"
  }
}
```

不传 `type` 时会先识别再求解。

点选格子：

```http
POST /createTask
{
  "clientKey": "和 .env 相同",
  "type": "AwsWafClassification",
  "question": "选出所有红绿灯",
  "images": ["base64格子1", "base64格子2"]
}
```

`getTaskResult` 里的 `solution.objects` / `indexes` 是要点的 0 起序号。一张整图可加 `rows`、`columns` 切开。

## API 完整调用示例

所有求解接口都需要 key。key 可以放在 JSON 的 `clientKey` 字段中，也可以放在
`x-client-key`、`x-api-key` 或 `Authorization: Bearer` 请求头中。下面使用 JSON
字段示例。

图片 OCR：

```bash
IMAGE_B64="$(base64 -w 0 captcha.png)"

curl -sS https://challenge.cool.pp.ua/createTask \
  -H 'Content-Type: application/json' \
  -d "{\n    \"clientKey\": \"replace_with_shared_key\",\n    \"task\": {\n      \"type\": \"ImageToTextTask\",\n      \"module\": \"common\",\n      \"websiteURL\": \"https://support.euserv.com\",\n      \"body\": \"$IMAGE_B64\"\n    }\n  }"
```

响应中的 `taskId` 需要继续轮询：

```bash
curl -sS https://challenge.cool.pp.ua/getTaskResult \
  -H 'Content-Type: application/json' \
  -d '{
    "clientKey": "replace_with_shared_key",
    "taskId": "replace_with_task_id"
  }'
```

处理中返回 `status=processing`，完成后返回 `status=ready` 和
`solution.text`。错误响应会带有 `errorId=1`、`errorCode` 和
`errorDescription`。

健康检查不需要 key：

```bash
curl -sS https://challenge.cool.pp.ua/health
```

## 从签到机使用

把 NodeSeek 的 `.env` 改成：

```env
SOLVER_TYPE=turnstile
API_BASE_URL=https://challenge.cool.pp.ua
CLIENTT_KEY=和求解器相同
```

## 访问控制

HTTPS 只保证传输加密。真正能解题的接口必须带 `clientKey`，和 `.env` 里的 `CLIENTT_KEY` 相同。

浏览器打开域名不会再看到服务清单。`/docs` 已关闭。没密钥的 `/detect`、`/createTask`、`/solve` 会返回 403。

不要把 `CLIENTT_KEY` 放进浏览器插件或网页前端，因为浏览器用户可以读取它。
如果 key 泄露，需要修改服务器 `.env` 后重启容器，并同步修改所有调用方。
