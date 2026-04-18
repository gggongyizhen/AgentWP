# Freakquency

## 题目信息

- 类型：Forensics / Misc
- 题目状态：已解出
- 题目附件：`hidden_message.wav`
- 题目描述：

```text
You have the audacity to match my freak?
```

- 核心突破点：把音频转成频谱图后，图中直接出现了一串 Base64；解码即可得到 flag

## 入口与现象

附件只有一个 `wav` 文件，先看基础信息：

```text
Duration: 00:00:27.00
Audio: pcm_f32le, 44100 Hz, mono
```

题面标题是 `Freakquency`，描述里也在强调 `freak`，基本就在往“频率 / 频谱”这个方向引。既然是音频取证题，而且没有额外文本或压缩包，最低成本的验证就是先看频谱图。

## 分析过程

### 1. 生成频谱图

直接用 `ffmpeg` 把音频渲染成频谱图：

```powershell
ffmpeg -y -i hidden_message.wav -lavfi showspectrumpic=s=2048x1024:legend=disabled -frames:v 1 spectrogram.png
```

生成后查看 `spectrogram.png`，可以在图中下部直接看到一串明显可疑的字符：

```text
VURDVEZ7dzB3X3kwdV9jNG5faDM0cl80X2YxbDM/fQ==
```

这串内容只包含 Base64 合法字符，并且还带有结尾补位 `==`，因此可以直接进入下一步。

### 2. Base64 解码

对上面的字符串做 Base64 解码：

```powershell
@'
import base64
s = 'VURDVEZ7dzB3X3kwdV9jNG5faDM0cl80X2YxbDM/fQ=='
print(base64.b64decode(s).decode())
'@ | python -
```

输出为：

```text
UDCTF{w0w_y0u_c4n_h34r_4_f1l3?}
```

到这里 flag 就拿到了。

## 利用过程

1. 检查附件，确认只有一个音频文件 `hidden_message.wav`。
2. 根据题目名 `Freakquency` 判断方向是频域分析，而不是时域或文件尾追加。
3. 用 `ffmpeg` 生成频谱图。
4. 在频谱图中读出隐藏的 Base64 字符串。
5. 对字符串做 Base64 解码，得到最终 flag。

## 关键 payload / 命令

```powershell
ffmpeg -y -i hidden_message.wav -lavfi showspectrumpic=s=2048x1024:legend=disabled -frames:v 1 spectrogram.png

@'
import base64
print(base64.b64decode('VURDVEZ7dzB3X3kwdV9jNG5faDM0cl80X2YxbDM/fQ==').decode())
'@ | python -
```

## Flag

```text
UDCTF{w0w_y0u_c4n_h34r_4_f1l3?}
```

## 总结

这题本质上就是频谱隐写。题目没有额外干扰项，真正有效的提示只有标题 `Freakquency`，它把分析方向直接指向了 frequency。只要把音频转成 spectrogram，隐藏信息就会以文本形式出现，剩下只是一次标准的 Base64 解码。
