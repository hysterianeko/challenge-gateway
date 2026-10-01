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
# 填写 CLIENTT_KEY、DOMAIN、ACME_EMAIL
docker compose up -d --build
curl -s https://challenge.cool.pp.ua/health
```

域名必须先解析到这台机器。证书由 Caddy 自动续签，不用 certbot。

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
