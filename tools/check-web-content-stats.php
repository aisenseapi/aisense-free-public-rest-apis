<?php
/** Tests for the web box content inventory helper. */

require_once dirname( __DIR__ ) . '/web/m2m-content-stats.php';

$passed = 0;
$failed = 0;

$check = function ( $condition, $label ) use ( &$passed, &$failed ) {
    if ( $condition ) {
        $passed++;
        echo "  ok    {$label}\n";
    } else {
        $failed++;
        echo "  FAIL  {$label}\n";
    }
};

$root = rtrim( sys_get_temp_dir(), '/\\' ) . '/aisense-web-content-' . bin2hex( random_bytes( 6 ) );
$content = $root . '/content/2026/08/29';
$assets = $root . '/assets';
mkdir( $content, 0755, true );
mkdir( $assets, 0755, true );

file_put_contents( $root . '/index.html', '<a href="/about">About</a>'
    . '<a href="https://example.com/secret">Outside</a>'
    . '<a href="/missing">Missing</a>'
    . '<form action="/upload" method="post"><input type="file" name="file"></form>' );
file_put_contents( $root . '/about.html', '<p>About</p>' );
file_put_contents( $assets . '/site.css', 'body{}' );
file_put_contents( $content . '/private-record.json', json_encode( array(
    'content'=>array( 'text'=>'NEVER-RETURN-THIS', 'links'=>array( 'https://one.example', 'https://two.example' ) ),
    'structure'=>array( '@type'=>'TechArticle' ),
    'ai_meta'=>array(
        'token_est'=>123,
        'embedding_ready'=>true,
        'expires'=>'2026-08-28T00:00:00Z',
    ),
) ) );
file_put_contents( $content . '/private-record.md', 'secret markdown' );

$inventory = m2m_content_inventory( 'data', array(
    'host'=>'data.aisenseapi.com',
    'root'=>$root,
    'published_dir'=>$root . '/content',
    'published_retention_days'=>180,
), 1787961600 );

$check( $inventory['files']['count'] === 5, 'all public files counted' );
$check( $inventory['files']['groups']['pages']['count'] === 2, 'page files grouped' );
$check( $inventory['files']['groups']['styles']['count'] === 1, 'style files grouped' );
$check( $inventory['files']['groups']['structured']['count'] === 2, 'structured files grouped' );
$check( $inventory['markup']['links'] === 3, 'links counted' );
$check( $inventory['markup']['internal_links'] === 2, 'internal links counted' );
$check( $inventory['markup']['external_links'] === 1, 'external links counted' );
$check( $inventory['markup']['broken_internal_links'] === 1, 'missing internal target marked' );
$check( $inventory['markup']['forms'] === 1, 'form counted' );
$check( $inventory['markup']['upload_forms'] === 1, 'upload form counted' );
$check( $inventory['published']['records'] === 1, 'published record counted' );
$check( $inventory['published']['files'] === 2, 'record and companion file counted' );
$check( $inventory['published']['expired'] === 1, 'expired published record marked' );
$check( $inventory['published']['token_estimate'] === 123, 'token estimate aggregated' );
$check( $inventory['published']['embedding_ready'] === 1, 'embedding-ready record counted' );
$check( $inventory['published']['content_links'] === 2, 'links inside published data aggregated' );
$check( $inventory['published']['types']['tech_article'] === 1, 'document type allowlisted' );

$encoded = json_encode( $inventory );
$check( strpos( $encoded, 'NEVER-RETURN-THIS' ) === false, 'published text is not returned' );
$check( strpos( $encoded, 'private-record' ) === false, 'published filename is not returned' );
$check( strpos( $encoded, 'example.com/secret' ) === false, 'link target is not returned' );
$check( strpos( $encoded, $root ) === false, 'filesystem root is not returned' );

$endpoint = file_get_contents( dirname( __DIR__ ) . '/web/m2m-logs.php' );
$check( strpos( $endpoint, "'inventory'" ) !== false, 'web M2M exposes the inventory action' );
$check( strpos( $endpoint, "m2m-content-stats.php" ) !== false, 'web M2M loads the aggregate-only scanner' );

$iterator = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator( $root, FilesystemIterator::SKIP_DOTS ),
    RecursiveIteratorIterator::CHILD_FIRST
);
foreach ( $iterator as $entry ) {
    if ( $entry->isFile() || $entry->isLink() ) {
        @unlink( $entry->getPathname() );
    } else {
        @rmdir( $entry->getPathname() );
    }
}
@rmdir( $root );

echo "\n{$passed} passed, {$failed} failed\n";
exit( $failed === 0 ? 0 : 1 );
