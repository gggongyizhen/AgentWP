# The Onion

## 题目信息

- 类型：Crypto
- 题目状态：已解出
- 题目附件：`challenge.txt`
- 题目描述：

```text
Can you peel back the layers?
NOTE: The answer you get will not have the CIT{} wrapper, make sure you add it to the final answer.
```

- 核心突破点：附件内容不是复杂密码算法，而是重复套了很多层 Base64；连续剥 15 层后得到最终字符串，再按题目要求补上 `CIT{}` 即可

## 入口与现象

附件 `challenge.txt` 里只有一长串文本：

```text
Vm0wd2QyUXlVWGxWV0d4V1YwZDRWMVl3WkRSWFJteFZVMjA1VjAxV2JETlhhMk0xVmpGYWMySkVUbGhoTVVwVVZtcEdTMk15U2tWVWJHaG9UVlZ3VlZadGNFSmxSbGw1VTJ0V1ZXSkhhRzlVVmxaM1ZsWmFkR05GZEZSTlZUVkpWbTEwVjFWdFNsWlhiRkpYWVd0d2RscFdXbUZrUjFaSFYyMTRVMkpIZHpGV2EyUXdZekpHYzFOdVVsWmhlbXhoVm1wT2IyRkdjRmRYYlVaclVsUkdWbFpYZUhkV01ERkZVbFJHVjJFeVVYZFpla3BIWXpGT2RWVnNXbWhsYlhob1ZtMXdUMVV5UmtkV1dHaFlZbFZhY1ZadGRHRk5SbFowWlVoa1YwMUVSbGRaTUZaM1ZqSktWVkpZWkZwbGEzQklXWHBHVDJSV1duTlRiV3hUVFcxb1dsWXhaRFJpTWtsM1RVaG9XR0pIVWxsWmJGWmhZMnhXYzFWclpGZGlSbkJaV2xWYVQxWlhTbFpqUldSYVRVWndlbFpxUm1GT2JFWlpZVVprVTFKWVFrbFdiWEJIVkRGa1YyTkZaR2hTTW5oVVZGY3hiMWRzV1hoYVJGSnBUV3RzTlZadE5VOVdiVXBIVjJ4U1dtSkhhRlJXTUZwVFZqSkdSbFJzVG1sU2JrSmFWMnhXYjJFeFdYZE5WVlpUWVRGd1YxbHJXa3RTUmxweFUydGFiRlpzU2xwWlZWcGhZVWRGZUdOR2FGaGlSbkJvVmtSS1QyUkdUbkphUmxKcFZqSm9lbGRYZUc5aU1XUlhWMWhvV0dKWVVrOVZiVEUwVjBaYVIyRkhPV2hpUlhBd1dWVm9UMVp0Um5KVGJXaGFUVlp3ZWxreWVHdGtSa3AwWlVaa2FWWnJiekZXYlhCS1RWZEZlRmRZWkU1V1ZscFVXV3RrVTFsV1VsWlhibVJzWWtad2VGVnRNVWRVTWtwR1YyeHdXbFpXY0doWmEyUkdaV3hHY21KR1pHbFhSVXBKVm10U1MxVXhXWGhXYmxaV1lsaENWRmxZY0ZkWFZscFlZMFU1YVUxWFVucFdNV2h2V1ZaS1IxTnVRbFZXYkhCWVZGUkdVMVp0UmtoUFZtUk9WakZLU2xkV1ZtRmpNV1IwVTJ0a1dHSlhhR0ZVVmxwM1pXeHJlVTFWWkZOaVJrcDZWa2N4YzFVeVNuSlRiVVpYVFc1b1dGbHFTa1psUm1SWldrVTFXRkpZUWxwV2JYUlhaREZrUjJKSVRtaFNhelZQVkZaYWQyVkdWWGxrUjBacFVtdHNNMVJzVm5kV01ERnhVbXRvVjFaRldreFdha3BQVWxaa2MxcEhiRmhTVlhCS1ZtMTBVMU14VlhoWFdHaFlZbXhhVjFsc1pHOVdSbXhaWTBaa2JHSkhVbGxhVldNMVlWVXhXRlZyYUZkTmFsWlVWa2Q0VDFOSFJrZFJiRnBwVmtWVmQxWnRjRWRWTVZwMFVtdG9VRll5YUZoWlZFNURUbXhrVlZGdFJtcE5WMUl3VlRKMGExZEhTbGhoUm1oYVZrVmFNMVpyV21GalZrcDFXa1pPVGxacmIzZFhiRlpyWXpGVmVWTnNiRnBOTW1oWVdWUkdkMkZHV2xWU2JGcHNVbTFTTVZVeWN6RlhSa3BaVVd4c1dGWnRVVEJhUkVaYVpVWmtkVkpzVm1sV1IzaFFWa1phWVdReVZrZFdibEpPVmxkU1ZsUlhkSGRTTVd0M1YyNWtXRkl3VmpSWk1GSlBWMnhhV0ZWclpHRldNMmhJV1RJeFMxSXhjRWhpUm1oVFZsaENTMVp0TVRCVk1VbDVVbGhvV0ZkSGVGWlpWRVozWVVaV2NWTnRPVmRTYkVwWlZHeGpOVll4V25OalJXaFlWa1UxZGxsV1ZYaFhSbFp5WVVaa1RtRnNXbFZXYTJRMFdWWkplRlJ1VWxCV2JGcFlWRlJHUzA1c1draGtSMFpYWWxaYVdWWlhkRzloTVVsNVlVaENWbUpIYUVSV01WcGhZMVpPY1ZWc1drNVdNVWwzVmxkNGIyTXlSa2RUYkdSVVlsVmFhRlpxVGxOaFJteFdWMjVLYkZKdFVubGFSV1F3VlRKRmVsRnFXbGRpUjFFd1dWUktSMWRHU2xsYVIzQlRWak5vV1ZkWGVHOVJNVTE0WTBaYVYxZEhhRlZWYlhSM1pWWmtjbGRzVGxoU2EydzFXVlZhZDFkR1dqWlJhbEpWWVRGd1lWcFZXbGRqTVhCSVVteE9iR0pZYUZGV2ExcGhXVmRSZVZaclpGZGliRXB5Vld0V1MySXhiRmxqUldSc1ZteEtlbFp0Tld0V01ERkZVbXBHV2xaWGFFeFdha3BIWTJ4a2NtVkdaR2hoTTBKUlZsUkNWazVXV1hoalJXUmhVbFJXVDFWc2FFTlRNVnB4VW0xR1ZrMVZNVFJXVnpWVFZqSktTRlZzV2xwaVdGSXpXVlZhVjJSRk1WZFViWEJUWWtad05GWlhNVEJOUmxsNFYyNU9hbEpYYUZoV2FrNVRWRVpzVlZGWWFGTldhM0I2VmtkNFlWVXlTa1pYV0hCWFZsWndSMVF4V2tOVmJFSlZUVVF3UFE9PQ==
```

这串内容只包含 Base64 合法字符，而且长度很大，没有任何分隔符、标点或自然语言特征。结合题目名 `The Onion` 和描述里的 `peel back the layers`，最合理的第一假设就是“多层套娃编码”。

## 分析过程

### 1. 先验证是不是多层 Base64

用一个很短的脚本循环 Base64 解码，并在每一层打印结果长度和前几个字符：

```powershell
@'
import base64, re
from pathlib import Path

s = Path("challenge.txt").read_text().strip()

for i in range(1, 21):
    b = base64.b64decode(s, validate=True)
    print(f"layer {i}: len={len(b)} sample={b[:32]!r}")

    try:
        s = b.decode().strip()
    except UnicodeDecodeError:
        break

    if not re.fullmatch(r"[A-Za-z0-9+/=\r\n]+", s):
        break
'@ | python -
```

输出可以看到前面很多层解出来依然是 Base64 文本，而且长度在稳定缩短：

```text
layer 1: len=1960 sample=b'Vm0wd2QyUXlVWGxWV0d4V1YwZDRXRmxU'
layer 2: len=1468 sample=b'Vm0wd2QyUXlVWGxWV0d4WFlUSm9WMVl3'
layer 3: len=1100 sample=b'Vm0wd2QyUXlVWGxXYTJoV1YwZG9WVll3'
...
layer 13: len=60 sample=b'WWprME9EWmpOelJqTnpjNVpHSTFNVGsw'
layer 14: len=44 sample=b'Yjk0ODZjNzRjNzc5ZGI1MTk0ZDY1MDhi'
layer 15: len=33 sample=b'b9486c74c779db5194d6508bebbee72b'
```

到第 15 层时，输出已经不再是新的 Base64 套娃，而是一个 32 位十六进制字符串：

```text
b9486c74c779db5194d6508bebbee72b
```

继续把它当 Base64 解只会得到一段二进制数据，不会再回到可读文本，因此这里就是应该停止的位置。

### 2. 提取最终答案

既然题目说明“你拿到的答案不会自带 `CIT{}` 包装”，那就说明解码出来的这一串文本本身就是 flag 主体。最短复现脚本如下：

```powershell
@'
import base64
from pathlib import Path

s = Path("challenge.txt").read_text().strip()
for _ in range(15):
    s = base64.b64decode(s).decode().strip()

print(s)
'@ | python -
```

输出：

```text
b9486c74c779db5194d6508bebbee72b
```

按题面要求补上 wrapper 后，最终 flag 为：

```text
CIT{b9486c74c779db5194d6508bebbee72b}
```

## 利用过程

1. 打开附件，发现只有一长串由 Base64 合法字符组成的文本。
2. 结合题目名 `The Onion` 判断方向是“分层剥离”，优先验证重复编码而不是复杂密码算法。
3. 编写循环脚本逐层 Base64 解码，观察每一层的输出形态。
4. 连续解 15 层后，拿到稳定的十六进制字符串 `b9486c74c779db5194d6508bebbee72b`。
5. 根据题面提示，给该字符串补上 `CIT{}`，得到最终 flag。

## 关键 payload / 命令

```powershell
@'
import base64
from pathlib import Path

s = Path("challenge.txt").read_text().strip()
for _ in range(15):
    s = base64.b64decode(s).decode().strip()

print(f"CIT{{{s}}}")
'@ | python -
```

## Flag

```text
CIT{b9486c74c779db5194d6508bebbee72b}
```

## 总结

这题的关键不是识别某种特殊密码，而是先根据题目名建立一个正确的低成本假设。`The Onion` 明确暗示“层”，附件内容又完全符合 Base64 形态，所以最优路线就是写脚本循环解码并观察每一层的产物。真正的答案藏在第 15 层，最后只需要按题面补上 flag wrapper。
