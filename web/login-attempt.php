<?php
// Retired shadow login. Account credentials belong only at the API customer portal.
http_response_code(410);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
echo json_encode(['error'=>'Use https://aisenseapi.com/customer/login']);
