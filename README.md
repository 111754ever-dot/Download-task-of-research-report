# 慧博研报批量下载器

一个**慢速、稳妥、可断点续传**的小工具,帮你把慧博里符合条件的研报一篇篇自动下下来,
不用手动点几百次。设计上刻意做得"慢而稳",行为接近真人操作,尽量不给服务器压力。

> 目标示例:下载「华创证券」在 2026-01-01 ~ 2026-07-25 发布的「宏观经济」研报。
> 这些条件都可以在 `config.py` 里改。

---

## 它是怎么工作的(三步)

1. **建目录**:先只翻列表、把符合条件的研报信息存进 `manifest.csv`,**不下载**。
   你可以先打开这个表格,核对数量、日期、标题对不对。
2. **下载**:按目录一篇篇慢慢下,每篇之间随机等 8~20 秒,每 12 篇多歇一会儿。
   中途断了没关系,重跑会自动从断点接着下。
3. **校验**:检查下下来的文件是不是完整的 PDF,坏的会自动标记、下次补下。

---

## 安全设计(为什么不容易出问题)

- **单线程**,一次只下一个,绝不并发。
- **随机间隔** + **分批休息** + **每小时上限**,节奏像人不像机器。
- **连续失败 3 次自动停机**:一旦登录过期或被限速,立刻停,不硬刚。
- **只用你已登录的会话**(Cookie),不碰你的账号密码。
- 你的 Cookie 存在 `config.py`,已被 `.gitignore` 排除,不会上传。

这些参数都在 `config.py` 底部,想更保守就把数字调大。

---

## 使用步骤

### 0. 装依赖

```bash
pip install -r requirements.txt
```

### 1. 填配置

慧博的接口地址、参数和网页解析都**已经在 `config.example.py` 里配好了**,
你只需要从抓包里填几个会过期的凭证。先复制一份:

```bash
cp config.example.py config.py      # Windows: copy config.example.py config.py
```

打开 `config.py`,只填最上面 ★ 标的那几项:

- `COOKIE` —— 抓到的那条请求"请求头"里 `Cookie:` 后面的一整段
- `ABC / DEF / VIDD / KEYY / XYZ` —— 在"请求体"最底下那行里,形如 `abc=… def=…` 的值

用桌面终端抓包用 **Fiddler**(见文末),抓到搜索请求后按上面对应填入即可。
这几项会过期,哪天跑不动了,重抓一次、更新这几项就行。

### 3. 先建目录,核对

```bash
python downloader.py manifest
```

跑完打开 `manifest.csv`,确认里面就是你要的那些华创宏观研报、数量也对得上。**这一步不下载,很安全。**

### 4. 开始下载

```bash
python downloader.py download
```

慢慢跑,可能要几个小时,可以随时 `Ctrl+C` 停,之后再跑会自动续传。文件在 `downloads/` 里。

### 5. 校验(可选)

```bash
python downloader.py verify
```

---

## 常见问题

- **中途停了 / 关机了?** 直接再跑 `python downloader.py download`,已下的自动跳过。
- **提示连续失败自动停了?** 多半是登录过期(重新登录、更新 `config.py` 里的 Cookie)或被临时限速(隔一两小时再跑)。
- **想下得更慢更稳?** 调大 `config.py` 里的 `MIN_DELAY / MAX_DELAY / BATCH_REST`,调小 `HOURLY_CAP`。

---

## 附:用 Fiddler 抓那几个凭证(桌面终端)

1. 装 **Fiddler Classic**(免费):`https://www.telerik.com/fiddler/fiddler-classic`
2. 打开后:`Tools → Options → HTTPS`,勾上 **Capture HTTPS CONNECTs** 和 **Decrypt HTTPS traffic**,
   弹出装证书时点 **Yes**,确定。
3. 按 `Ctrl+X` 清空列表,回到慧博点一下"下一页"。
4. 在 Fiddler 里找到 **Host 是 `sysdw.hibor.com.cn`、URL 是 `/huisouchrome/sa`** 的那一行,点它。
5. 右边 `Inspectors` → 上半部分 `Raw`:
   - 找到 `Cookie:` 那一整行 → 填进 `config.py` 的 `COOKIE`
   - 找到最底下的请求体,里面 `abc=… def=… vidd=… keyy=… xyz=…` → 分别填进对应项

---

## 使用提醒

请把下载的研报用于**个人研究**,遵守你与平台之间的协议,不要二次分发这些版权内容。
