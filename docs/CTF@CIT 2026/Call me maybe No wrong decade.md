# Call me, maybe? No… wrong decade.

## 题目信息

- 类型：Misc
- 题目状态：已解出
- 题目附件：无
- 题目描述：

```text
I don't have a witty description for this one...

$2b$10$Ni0U3D5ibg1NY6G/k8CDHuXG7m/WNZzuV/9PDPnRzgKs4wUjaTwGO

FLAG FORMAT: CIT{password}
```

- 核心突破点：题目真正的提示不在哈希本身，而在标题。`Call me, maybe?` 明确在提示“你想到的那首歌不对年代”，继续往前找电话相关的经典流行文化梗，很容易落到 Tommy Tutone 的 `867-5309/Jenny`。把由此得到的候选字符串拿去做 bcrypt 校验即可命中真实密码。

## 入口与现象

这题没有附件，也没有交互点，只有一条 bcrypt 哈希：

```text
$2b$10$Ni0U3D5ibg1NY6G/k8CDHuXG7m/WNZzuV/9PDPnRzgKs4wUjaTwGO
```

如果直接把它当成普通爆破题来做，成本会比较高，因为 bcrypt 本身就故意设计得比较慢。这里更值得优先利用的是题目名：

```text
Call me, maybe? No… wrong decade.
```

`Call Me Maybe` 是 2012 年的歌，而题目又补了一句 `wrong decade`，说明出题人在明确告诉你：方向确实和“打电话/歌名”有关，但答案不是这首 2010 年代的歌。

## 分析过程

### 1. 从题目名反推文化梗

既然题目强调“打电话”和“年代不对”，最自然的思路就是往更早年代的电话相关流行歌上收缩。这里最典型、也最符合 CTF 出题习惯的就是：

```text
867-5309/Jenny
```

这是 Tommy Tutone 在 1981 年发行的歌。它本身就是一个非常出名的“电话号码”梗，所以和题目标题的关联度很高：

- `Call me` 对应电话主题。
- `wrong decade` 把你从 2012 年拉回 1980 年代。
- `FLAG FORMAT: CIT{password}` 说明最终要的是“密码明文”，不是再做额外变换。

到这一步其实就不该盲跑大字典了，而应该围绕这个提示构造少量高价值候选词，例如：

- `8675309`
- `jenny`
- `8675309jenny`
- `867-5309`

### 2. 用 bcrypt 逐个验证候选值

我本地直接用 Python 的 `bcrypt` 模块校验这些候选值：

```python
import bcrypt

hashv = b"$2b$10$Ni0U3D5ibg1NY6G/k8CDHuXG7m/WNZzuV/9PDPnRzgKs4wUjaTwGO"
candidates = [
    "8675309",
    "jenny",
    "867-5309",
    "8675309jenny",
]

for s in candidates:
    if bcrypt.checkpw(s.encode(), hashv):
        print(s)
        break
```

输出结果：

```text
8675309jenny
```

这就说明 bcrypt 对应的原文密码就是 `8675309jenny`。

## 利用过程

1. 观察到题目只给了一条 bcrypt 哈希，直接暴力爆破不划算。
2. 把重点放到题目名 `Call me, maybe? No… wrong decade.`。
3. 识别出这是在把方向从 2012 年的 `Call Me Maybe` 往更早的电话相关歌曲上引导。
4. 结合 1980 年代最典型的电话歌 `867-5309/Jenny` 构造候选值。
5. 用 `bcrypt.checkpw()` 校验候选值，命中 `8675309jenny`。
6. 按题面要求补上 `CIT{}`，得到最终 flag。

## 关键 payload / 命令

```python
import bcrypt

hashv = b"$2b$10$Ni0U3D5ibg1NY6G/k8CDHuXG7m/WNZzuV/9PDPnRzgKs4wUjaTwGO"
print(bcrypt.checkpw(b"8675309jenny", hashv))
```

输出：

```text
True
```

## Flag

```text
CIT{8675309jenny}
```

## 总结

这题本质上不是密码学强度题，而是一个很短的“提示词 -> 流行文化梗 -> 定向校验”链路。真正决定解题效率的是先相信题目名在给方向，再用 bcrypt 去验证少量高质量候选值，而不是把它当成纯字典爆破题。
