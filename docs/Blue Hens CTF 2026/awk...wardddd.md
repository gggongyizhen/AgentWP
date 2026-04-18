# awk...wardddd ✂️

## 题目信息

- 类型：Forensics / Misc
- 题目状态：已解出
- 题目附件：`s0rry_in_4dv4nc3.zip`
- 题目描述：

```text
We recovered a directory from a misconfigured archive job. Most of the contents appear to be redundant or stale, but a few records still reflect the system’s original processing format. Focus on what remains consistent.
```

- 核心突破点：全量文件里只有 7 条记录同时满足 `profile=delta` 和 `state=active`，它们的 `data` 字段按 `part` 排序后正好拼成一段 Base64，解码即可得到 flag

## 入口与现象

附件解压后可以看到一个很“脏”的目录：

```text
s0rry_in_4dv4nc3/
├─ archive/
├─ logs/
├─ reports/
│  ├─ deep/
│  └─ old/
├─ tmp/
└─ users/
```

里面一共有 10008 个文件，文件名基本都是随机串，扩展名则平均分布在 `.log`、`.txt`、`.cache`、`.tmp`、`.rec`、`.dat` 之间。随便抽几份内容看，记录格式基本一致，都是这种键值对：

```text
timestamp=702428
profile=alpha
uid=85221
state=disabled
part=03
data=NAHRvJ5R
note=vtiPWVBDp4FrPSCS
comment=VURDVEZ7ZmFrZV9mbGFnfQ==
```

题面里最关键的一句是：

```text
Focus on what remains consistent.
```

说明重点不是盲目翻 1 万个文件，而是找出在大批“冗余/过期”记录里仍然保持一致、而且足够特殊的那一小撮。

## 分析过程

### 1. 先看哪些字段最异常

全量统计后可以发现：

- 绝大多数文件的 `profile` 只会出现在 `alpha / beta / gamma / omega`
- 绝大多数文件的 `state` 只会出现在 `pending / disabled / archived`
- `comment=` 只出现在 1483 个 8 行文件里，而且值全部相同，都是 `VURDVEZ7ZmFrZV9mbGFnfQ==`

把这串 Base64 解码后只是：

```text
UDCTF{fake_flag}
```

明显是干扰项。

继续筛全量记录，会发现只有 7 个文件同时满足两个异常条件：

- `profile=delta`
- `state=active`

可以直接用 `rg` 找出来：

```powershell
rg -n -l "^state=active$" awkward_work\s0rry_in_4dv4nc3
rg -n -l "^profile=delta$" awkward_work\s0rry_in_4dv4nc3
```

输出正好是同一组文件：

```text
awkward_work\s0rry_in_4dv4nc3\users\sys_FtSns_01.rec
awkward_work\s0rry_in_4dv4nc3\logs\sys_gL6JX_02.rec
awkward_work\s0rry_in_4dv4nc3\tmp\sys_t-Bfc_03.rec
awkward_work\s0rry_in_4dv4nc3\archive\sys_we9bk_04.rec
awkward_work\s0rry_in_4dv4nc3\archive\sys_eXAuo_05.rec
awkward_work\s0rry_in_4dv4nc3\logs\sys_tBxJ4_06.rec
awkward_work\s0rry_in_4dv4nc3\tmp\sys_lYOTr_07.rec
```

这 7 个文件还有几个共同点：

- 文件名都以 `sys_` 开头，不再是随机名
- 扩展名统一为 `.rec`
- `note` 固定为 `retained`
- `part` 刚好覆盖 `01..07`

这些特征已经很像“原始处理格式”保留下来的正式记录。

### 2. 读取这 7 条 retained 记录

逐个查看内容后，可以提取出每一段 `data`：

```text
part=01 -> VURDVEZ7
part=02 -> dzNsbF83
part=03 -> aDQ3X3c0
part=04 -> NW4nN183
part=05 -> MF9oNHJk
part=06 -> X3c0NV8x
part=07 -> Nz99
```

把它们按 `part` 顺序拼起来：

```text
VURDVEZ7dzNsbF83aDQ3X3c0NW4nN183MF9oNHJkX3c0NV8xNz99
```

这显然是一段合法 Base64。

### 3. Base64 解码得到 flag

解码后得到：

```text
UDCTF{w3ll_7h47_w45n'7_70_h4rd_w45_17?}
```

到这里 flag 就拿到了。

## 利用过程

1. 解压附件并确认目录里存在大量随机命名的冗余记录。
2. 抽样观察记录格式，识别出 `comment=UDCTF{fake_flag}` 这一类显式干扰项。
3. 对全量字段做统计，找出只出现 7 次的异常组合 `profile=delta + state=active`。
4. 发现这 7 个文件名统一以 `sys_` 开头，且 `part` 正好覆盖 `01..07`。
5. 读取每个文件的 `data` 字段，按 `part` 顺序拼接。
6. 对拼接结果做 Base64 解码，得到最终 flag。

## 关键 payload / 命令

下面这段 PowerShell 可以完整复现提取过程：

```powershell
$records = Get-ChildItem .\awkward_work\s0rry_in_4dv4nc3 -Recurse -File | ForEach-Object {
    $map = @{}
    foreach ($line in Get-Content -LiteralPath $_.FullName) {
        $k, $v = $line -split '=', 2
        $map[$k] = $v
    }
    if ($map['profile'] -eq 'delta' -and $map['state'] -eq 'active') {
        [PSCustomObject]@{
            Part = [int]$map['part']
            Data = $map['data']
            Path = $_.FullName
        }
    }
}

$joined = ($records | Sort-Object Part | Select-Object -ExpandProperty Data) -join ''
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($joined))
```

输出：

```text
UDCTF{w3ll_7h47_w45n'7_70_h4rd_w45_17?}
```

## Flag

```text
UDCTF{w3ll_7h47_w45n'7_70_h4rd_w45_17?}
```

## 总结

这题本质上不是文件恢复，而是一次字段一致性筛选。海量随机文件和 `fake_flag` comment 都是噪声，真正有效的是那 7 条仍然保留原始系统格式的 `delta + active + retained` 记录。把它们按 `part` 重组以后，剩下只是一次标准的 Base64 解码。
