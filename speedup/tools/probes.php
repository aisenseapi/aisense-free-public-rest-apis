<?php
/**
 * probes.php - the atom tests.
 *
 * Before composing a format, measure its alphabet. Each probe is one
 * construct repeated enough times for the per-construct cost to dominate the
 * calibration noise. The design questions each group answers:
 *
 *   sigil_*   which section/marker characters are cheap across vocabularies
 *   key_*     what a key-value pair costs in each syntax style
 *   dict_*    whether a header dictionary plus short references beats
 *             repeating full keys (the core .sp hypothesis)
 *   num_*     how numbers, timestamps and uuids tokenize
 *   sep_*     newline vs space vs tab vs pipe as separators
 *   ind_*     what indentation costs per level
 *   b64_*     the base64 trap, quantified once and for all
 *
 * Usage: php probes.php
 */

declare( strict_types = 1 );

$root = dirname( __DIR__ );
$dst  = $root . '/probes';
if ( !is_dir( $dst ) ) mkdir( $dst, 0755, true );

$R = 24; // repetitions per probe

$probes = [];

// sigils - each candidate marker, repeated on its own line
foreach ( [ 'hash'=>'#', 'tilde'=>'~', 'at'=>'@', 'pct'=>'%', 'pipe'=>'|', 'semi'=>';', 'bang'=>'!', 'caret'=>'^', 'gt'=>'>', 'dslash'=>'//' ] as $n => $s ){
    $probes[ "sigil_$n" ] = str_repeat( "$s section\n", $R );
}

// key-value syntax styles, same 6 keys repeated
$kv = [ 'id'=>1017, 'sku'=>'NUT-M6', 'qty'=>900, 'price'=>2.95, 'status'=>'shipped', 'ts'=>1786901617 ];
$json = ''; $yaml = ''; $eq = ''; $short = '';
for ( $i = 0; $i < $R; $i++ ){
    $j = [];
    foreach ( $kv as $k => $v ) $j[] = is_string( $v ) ? "\"$k\":\"$v\"" : "\"$k\":$v";
    $json  .= '{' . implode( ',', $j ) . "}\n";
    $y = [];
    foreach ( $kv as $k => $v ) $y[] = "$k: $v";
    $yaml  .= implode( "\n", $y ) . "\n";
    $e = [];
    foreach ( $kv as $k => $v ) $e[] = "$k=$v";
    $eq    .= implode( ' ', $e ) . "\n";
    $short .= "1017,NUT-M6,900,2.95,shipped,1786901617\n";
}
$probes['key_json']  = $json;
$probes['key_yaml']  = $yaml;
$probes['key_eq']    = $eq;
$probes['key_none']  = $short; // values only, order carries meaning

// the dictionary hypothesis: header once, short refs after
$probes['dict_full'] = str_repeat( "status:shipped qty:900 price:2.95\n", $R );
$probes['dict_ref']  = "!d s=status q=qty p=price\n" . str_repeat( "s:shipped q:900 p:2.95\n", $R );

// numbers and identifiers
$probes['num_unix']    = str_repeat( "1786901617\n", $R );
$probes['num_iso']     = str_repeat( "2026-08-17T15:33:37+00:00\n", $R );
$probes['num_decimal'] = str_repeat( "2.95 14.75 0.18 31.9\n", $R );
$probes['num_uuid']    = str_repeat( "6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91\n", $R );
$probes['num_short']   = str_repeat( "6f8c9e52\n", $R );

// separators around the same tokens
$words = 'alpha beta gamma delta epsilon zeta';
$probes['sep_space']   = str_repeat( $words . "\n", $R );
$probes['sep_comma']   = str_repeat( str_replace( ' ', ',', $words ) . "\n", $R );
$probes['sep_tab']     = str_repeat( str_replace( ' ', "\t", $words ) . "\n", $R );
$probes['sep_pipe']    = str_repeat( str_replace( ' ', '|', $words ) . "\n", $R );
$probes['sep_newline'] = str_repeat( str_replace( ' ', "\n", $words ) . "\n", $R );

// indentation cost per level
$probes['ind_none'] = str_repeat( "key: value\n", $R );
$probes['ind_2sp']  = str_repeat( "  key: value\n", $R );
$probes['ind_4sp']  = str_repeat( "    key: value\n", $R );
$probes['ind_tab']  = str_repeat( "\tkey: value\n", $R );

// the base64 trap, same payload three ways
$payload = 'The refire loop came from an mbstring call under cron CLI php.';
$probes['b64_plain']  = str_repeat( $payload . "\n", $R );
$probes['b64_base64'] = str_repeat( base64_encode( $payload ) . "\n", $R );
$probes['b64_hex']    = str_repeat( bin2hex( $payload ) . "\n", $R );

$manifest = "probe\tbytes\n";
foreach ( $probes as $name => $text ){
    file_put_contents( "$dst/$name.txt", $text );
    $manifest .= $name . "\t" . strlen( $text ) . "\n";
}
file_put_contents( "$dst/manifest.tsv", $manifest );
echo count( $probes ) . " probes written\n";
