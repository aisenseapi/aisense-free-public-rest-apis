<?php
/**
 * render.php - canonical corpus items to every baseline format.
 *
 * Deterministic on purpose: the same canonical JSON must always produce byte
 * identical renders, or measurements stop being comparable between runs.
 *
 * Formats: json_min, json_pretty, yaml, md, tsv, toon.
 * The TOON render follows the token-oriented notation's core ideas -
 * uniform arrays declared once as name[N]{fields} with bare comma rows,
 * indentation for nesting, unquoted strings - and is labelled an
 * approximation in every report. It exists to be beaten fairly, not to be
 * misrepresented.
 *
 * Usage: php render.php  (from anywhere; paths are resolved from this file)
 */

declare( strict_types = 1 );

$root = dirname( __DIR__ );
$src  = $root . '/corpus/canonical';
$dst  = $root . '/corpus/renders';

if ( !is_dir( $dst ) ) mkdir( $dst, 0755, true );

// ── scalar helpers ───────────────────────────────────────────────────────────

function sp_scalar( $v ): string
{
    if ( $v === null )  return 'null';
    if ( $v === true )  return 'true';
    if ( $v === false ) return 'false';
    return (string)$v;
}

function yaml_scalar( $v ): string
{
    if ( $v === null )  return 'null';
    if ( $v === true )  return 'true';
    if ( $v === false ) return 'false';
    if ( is_string( $v ) and preg_match( '/[:#\[\]{}\n]|^\s|\s$/', $v ) ){
        return '"' . str_replace( '"', '\"', $v ) . '"';
    }
    return (string)$v;
}

function is_uniform_array( $v ): bool
{
    if ( !is_array( $v ) or $v === [] or !array_is_list( $v ) ) return false;
    if ( !is_array( $v[0] ) ) return false;
    $keys = array_keys( $v[0] );
    foreach ( $v as $row ){
        if ( !is_array( $row ) or array_keys( $row ) !== $keys ) return false;
        foreach ( $row as $cell ) if ( is_array( $cell ) ) return false;
    }
    return true;
}

// ── yaml ─────────────────────────────────────────────────────────────────────

function to_yaml( $v, int $ind = 0 ): string
{
    $pad = str_repeat( '  ', $ind );
    $out = '';
    if ( is_array( $v ) and array_is_list( $v ) ){
        foreach ( $v as $item ){
            if ( is_array( $item ) ){
                $inner = ltrim( to_yaml( $item, $ind + 1 ) );
                $out .= $pad . "- " . $inner;
            } else {
                $out .= $pad . "- " . yaml_scalar( $item ) . "\n";
            }
        }
    } elseif ( is_array( $v ) ){
        foreach ( $v as $k => $val ){
            if ( is_array( $val ) and $val !== [] ){
                $out .= $pad . $k . ":\n" . to_yaml( $val, $ind + 1 );
            } elseif ( is_array( $val ) ){
                $out .= $pad . $k . ": []\n";
            } else {
                $out .= $pad . $k . ": " . yaml_scalar( $val ) . "\n";
            }
        }
    }
    return $out;
}

// ── markdown ─────────────────────────────────────────────────────────────────

function to_md( $v, int $depth = 2 ): string
{
    $out = '';
    foreach ( $v as $k => $val ){
        if ( is_uniform_array( $val ) ){
            $keys = array_keys( $val[0] );
            $out .= str_repeat( '#', $depth ) . " $k\n\n";
            $out .= '| ' . implode( ' | ', $keys ) . " |\n";
            $out .= '|' . str_repeat( ' --- |', count( $keys ) ) . "\n";
            foreach ( $val as $row ){
                $out .= '| ' . implode( ' | ', array_map( 'sp_scalar', $row ) ) . " |\n";
            }
            $out .= "\n";
        } elseif ( is_array( $val ) and array_is_list( $val ) ){
            $out .= str_repeat( '#', $depth ) . " $k\n\n";
            foreach ( $val as $item ){
                if ( is_array( $item ) ){
                    $parts = [];
                    foreach ( $item as $ik => $iv ){
                        $parts[] = "$ik: " . ( is_array( $iv ) ? json_encode( $iv, JSON_UNESCAPED_SLASHES ) : sp_scalar( $iv ) );
                    }
                    $out .= '- ' . implode( ', ', $parts ) . "\n";
                } else {
                    $out .= '- ' . sp_scalar( $item ) . "\n";
                }
            }
            $out .= "\n";
        } elseif ( is_array( $val ) ){
            $out .= str_repeat( '#', $depth ) . " $k\n\n" . to_md( $val, min( 6, $depth + 1 ) );
        } else {
            $out .= "- **$k**: " . sp_scalar( $val ) . "\n";
        }
    }
    return $out;
}

// ── tsv ──────────────────────────────────────────────────────────────────────

function to_tsv( $v ): string
{
    $out = '';
    foreach ( $v as $k => $val ){
        if ( is_uniform_array( $val ) ){
            $keys = array_keys( $val[0] );
            $out .= "# $k\n" . implode( "\t", $keys ) . "\n";
            foreach ( $val as $row ){
                $out .= implode( "\t", array_map( 'sp_scalar', $row ) ) . "\n";
            }
        } elseif ( is_array( $val ) ){
            $out .= "$k\t" . json_encode( $val, JSON_UNESCAPED_SLASHES ) . "\n";
        } else {
            $out .= "$k\t" . sp_scalar( $val ) . "\n";
        }
    }
    return $out;
}

// ── toon approximation ───────────────────────────────────────────────────────

function toon_cell( $v ): string
{
    if ( $v === null )  return 'null';
    if ( $v === true )  return 'true';
    if ( $v === false ) return 'false';
    if ( is_string( $v ) and ( str_contains( $v, ',' ) or str_contains( $v, "\n" ) ) ){
        return '"' . str_replace( '"', '\"', $v ) . '"';
    }
    return (string)$v;
}

function to_toon( $v, int $ind = 0 ): string
{
    $pad = str_repeat( '  ', $ind );
    $out = '';
    foreach ( $v as $k => $val ){
        if ( is_uniform_array( $val ) ){
            $keys = array_keys( $val[0] );
            $out .= $pad . $k . '[' . count( $val ) . ']{' . implode( ',', $keys ) . "}:\n";
            foreach ( $val as $row ){
                $out .= $pad . '  ' . implode( ',', array_map( 'toon_cell', $row ) ) . "\n";
            }
        } elseif ( is_array( $val ) and array_is_list( $val ) ){
            $out .= $pad . $k . '[' . count( $val ) . "]:\n";
            foreach ( $val as $item ){
                if ( is_array( $item ) ){
                    $out .= $pad . "  -\n" . to_toon( $item, $ind + 2 );
                } else {
                    $out .= $pad . '  - ' . toon_cell( $item ) . "\n";
                }
            }
        } elseif ( is_array( $val ) ){
            $out .= $pad . $k . ":\n" . to_toon( $val, $ind + 1 );
        } else {
            $out .= $pad . $k . ': ' . toon_cell( $val ) . "\n";
        }
    }
    return $out;
}

// ── main ─────────────────────────────────────────────────────────────────────

$manifest = [];
foreach ( glob( $src . '/*.json' ) as $file ){
    $name = basename( $file, '.json' );
    $data = json_decode( file_get_contents( $file ), true );
    if ( $data === null ) { fwrite( STDERR, "bad canonical: $name\n" ); exit( 1 ); }

    $renders = [
        'json_min'    => json_encode( $data, JSON_UNESCAPED_SLASHES ),
        'json_pretty' => json_encode( $data, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT ),
        'yaml'        => to_yaml( $data ),
        'md'          => to_md( $data ),
        'tsv'         => to_tsv( $data ),
        'toon'        => to_toon( $data ),
    ];
    foreach ( $renders as $fmt => $text ){
        $out = "$dst/$name.$fmt.txt";
        file_put_contents( $out, $text );
        $manifest[] = [ $name, $fmt, strlen( $text ) ];
    }
}

$lines = "item\tformat\tbytes\n";
foreach ( $manifest as $m ) $lines .= implode( "\t", $m ) . "\n";
file_put_contents( "$dst/manifest.tsv", $lines );
echo count( $manifest ) . " renders written\n";
