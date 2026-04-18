# Name Calling

## 题目信息

- 类型：Forensics
- 题目状态：已解出
- 题目附件：`yousaidwhat.pcapng`
- 题目描述：

```text
I think someone called you chicken. You should do something about it
```

- 核心突破点：流量包里有不少干扰请求，但真正有价值的是一个被加密的 `zip` 和一张 `chicken.jpg`；`chicken.jpg` 的 EXIF `Copyright` 字段里藏了一段十六进制字符串，解码后正好是压缩包密码

## 入口与现象

这题给的是一份 `pcapng`，题面又明确提到了 `chicken`，所以第一步先把流量里真正下载过的对象找出来。

我本地没有 `tshark`，所以直接用 `scapy` 读包，把 `172.16.248.1 -> 172.16.248.147:8000` 的 HTTP 请求筛出来：

```python
from scapy.all import rdpcap, IP, TCP, Raw

pkts = rdpcap("yousaidwhat.pcapng")
for i, p in enumerate(pkts, 1):
    if IP in p and TCP in p and Raw in p:
        ip = p[IP]
        tcp = p[TCP]
        raw = bytes(p[Raw]).decode("latin1", "replace")
        if tcp.dport == 8000 and raw.startswith("GET "):
            print(i, raw.split("\\r\\n", 1)[0])
```

筛出来的关键请求如下：

```text
GET /whoareyoucalling.zip HTTP/1.1
GET /whossliming.jpg HTTP/1.1
GET /stinky.jpeg HTTP/1.1
GET /chicken.jpg HTTP/1.1
```

另外还有很多 `decoy1.txt` / `decoy2.txt`，但响应全是 `404 File not found`，明显只是干扰项。

## 分析过程

### 1. 先还原 HTTP 响应体

把 TCP 载荷按流重组后，可以把这些文件直接从流量包里导出来。导出结果里最值得注意的是：

- `whoareyoucalling.zip`：`200 OK`
- `whossliming.jpg`：`200 OK`
- `stinky.jpeg`：`200 OK`
- `chicken.jpg`：`200 OK`

其中 `whoareyoucalling.zip` 只有 243 字节，非常小，打开后发现里面只有一个文件 `whoareyoucalling.txt`，而且被加密了：

```python
import zipfile

with zipfile.ZipFile("whoareyoucalling.zip") as z:
    print(z.namelist())
    print(z.infolist()[0].flag_bits)
```

可以确认压缩包里有东西，但需要密码。

### 2. 题面点名 `chicken`，先查 `chicken.jpg`

既然题面说“someone called you chicken”，那最自然的高价值线索就是 `chicken.jpg`。

直接看图片本身只是一只鸡，没有肉眼可见的隐藏文本，所以继续查元数据：

```python
from PIL import Image, ExifTags

img = Image.open("chicken.jpg")
for k, v in img.getexif().items():
    print(k, ExifTags.TAGS.get(k, k), v)
```

输出里最关键的一项是：

```text
33432 Copyright 6e6f626f64792063616c6c73206d6520636869636b656e21
```

这串值看起来不像正常版权信息，更像十六进制编码。解码一下：

```python
bytes.fromhex("6e6f626f64792063616c6c73206d6520636869636b656e21").decode()
```

得到：

```text
nobody calls me chicken!
```

这句话和题面完全对应，而且非常像压缩包密码。

### 3. 用 EXIF 里的句子解压 zip

直接拿这句话去解 `whoareyoucalling.zip`：

```python
import zipfile

with zipfile.ZipFile("whoareyoucalling.zip") as z:
    data = z.read("whoareyoucalling.txt", pwd=b"nobody calls me chicken!")
    print(data.decode())
```

成功得到：

```text
UDCTF{wh4ts_wr0ng_mcf1y}
```

## 利用过程

1. 从 `pcapng` 中筛出真正成功下载的 HTTP 对象，忽略 `404` 的 `decoy` 请求。
2. 发现有一个被加密的 `whoareyoucalling.zip`，说明题目大概率要从其它文件里找密码。
3. 根据题面和文件名优先检查 `chicken.jpg`。
4. 在 EXIF `Copyright` 字段里拿到十六进制字符串。
5. 将其解码为 `nobody calls me chicken!`。
6. 用这句话作为 zip 密码，解出 `whoareyoucalling.txt`，拿到 flag。

## 关键 payload / 命令

```python
from PIL import Image
import zipfile

img = Image.open("chicken.jpg")
hex_text = img.getexif()[33432]
password = bytes.fromhex(hex_text).decode()
print(password)

with zipfile.ZipFile("whoareyoucalling.zip") as z:
    print(z.read("whoareyoucalling.txt", pwd=password.encode()).decode())
```

输出：

```text
nobody calls me chicken!
UDCTF{wh4ts_wr0ng_mcf1y}
```

## Flag

```text
UDCTF{wh4ts_wr0ng_mcf1y}
```

## 总结

这题的关键不是把所有流量都翻一遍，而是先用题面把注意力收敛到 `chicken` 相关对象上。真正决定胜负的是：

1. 识别 `decoy` 请求只是噪声。
2. 注意到 `zip` 被加密，必须从别的对象里找密码。
3. 在 `chicken.jpg` 的 EXIF 字段里发现十六进制字符串，并把它还原成压缩包密码。

整题就是一条很短的链：`pcapng -> chicken.jpg EXIF -> zip password -> flag`。
