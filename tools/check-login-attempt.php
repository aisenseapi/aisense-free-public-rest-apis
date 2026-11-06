<?php
/** The retired shadow form must never collect credentials or notify Slack again. */
declare(strict_types=1);
$root=dirname(__DIR__); $failed=0; $passed=0;
$check=static function(bool $ok,string $label) use(&$failed,&$passed): void { if ($ok) { $passed++; } else { $failed++; } echo ($ok?'ok   ':'FAIL ').$label.PHP_EOL; };
ob_start(); require $root.'/web/login-attempt.php'; $body=ob_get_clean();
$code=http_response_code();
$check($code===410,'shadow login is retired with 410');
$check((json_decode($body,true)['error']??'')==='Use https://aisenseapi.com/customer/login','retired handler points to real account portal');
$page=file_get_contents($root.'/web/login.html');
$check(str_contains($page,'https://aisenseapi.com/customer/login'),'sign-in link uses API domain');
$check(str_contains($page,'https://aisenseapi.com/customer/register'),'registration link is present');
$check(!str_contains($page,'type="password"') && !str_contains($page,'/login-attempt.php'),'www collects no account password and no longer calls shadow handler');
$handler=file_get_contents($root.'/web/login-attempt.php');
$check(!str_contains($handler,'slack_alert') && !str_contains($handler,'$_POST'),'old handler neither reads credentials nor sends notifications');
$checked=0;
foreach (glob($root.'/web/*.html') as $file) {
 $html=file_get_contents($file); if (!str_contains($html,'class="theme-toggle"')) { continue; }
 $checked++; if (!preg_match('~class="theme-toggle".*?</button><a class="account-login" href="/login" aria-label="Sign in or register"~s',$html)) { $check(false,basename($file).' missing adjacent sign-in control'); }
}
$check($checked>100,'all generated page headers carry the shared account control');
echo "check-login-attempt: $passed passed / $failed failed\n"; exit($failed?1:0);
