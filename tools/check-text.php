<?php

/**
 * Check public documentation for punctuation that is hard to type or easy to
 * introduce through generated text.
 *
 * Run from anywhere with: php tools/check-text.php
 */

declare( strict_types = 1 );

$root = dirname( __DIR__ );
$extensions = [ 'md', 'html', 'json', 'txt' ];
$patterns = [
    'en dash'=>'/\x{2013}/u',
    'em dash'=>'/\x{2014}/u',
    'curly single quote'=>'/[\x{2018}\x{2019}]/u',
    'curly double quote'=>'/[\x{201C}\x{201D}]/u',
    'ellipsis character'=>'/\x{2026}/u',
    'arrow character'=>'/[\x{2190}-\x{21FF}]/u',
    'middle dot'=>'/\x{00B7}/u',
    'invisible formatting character'=>'/[\x{200B}-\x{200F}\x{2060}\x{FEFF}]/u'
];
$failures = [];
$files_checked = 0;

$walker = new RecursiveIteratorIterator(
    new RecursiveCallbackFilterIterator(
        new RecursiveDirectoryIterator( $root, FilesystemIterator::SKIP_DOTS ),
        function ( SplFileInfo $entry ): bool {
            return $entry->getFilename() !== '.git';
        }
    )
);

foreach ( $walker as $file ){
    if ( !$file->isFile() ){
        continue;
    }

    if ( !in_array( strtolower( $file->getExtension() ), $extensions, true ) ){
        continue;
    }

    $contents = file_get_contents( $file->getPathname() );

    if ( $contents === false ){
        $failures[] = 'Could not read ' . $file->getPathname();
        continue;
    }

    $files_checked++;

    foreach ( $patterns as $label=>$pattern ){
        if ( preg_match( $pattern, $contents, $match, PREG_OFFSET_CAPTURE ) !== 1 ){
            continue;
        }

        $offset = $match[0][1];
        $line = substr_count( substr( $contents, 0, $offset ), "\n" ) + 1;
        $relative = str_replace( '\\', '/', substr( $file->getPathname(), strlen( $root ) + 1 ) );
        $failures[] = $relative . ':' . $line . ' contains ' . $label;
    }
}

if ( $failures !== [] ){
    foreach ( $failures as $failure ){
        fwrite( STDERR, '  FAIL  ' . $failure . "\n" );
    }

    fwrite( STDERR, "\ncheck-text: " . count( $failures ) . " problems found\n" );
    exit( 1 );
}

echo 'check-text: ' . $files_checked . " files passed\n";

