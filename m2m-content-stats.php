<?php
/**
 * Aggregate public content on the web box without returning content or names.
 *
 * This helper is included by m2m-logs.php. A direct web request gets nothing.
 * It is kept separate so the scanner can be tested with temporary fixtures.
 * Compatible with PHP 7.4 on the web box.
 */

if ( isset( $_SERVER['SCRIPT_FILENAME'] )
     && realpath( (string)$_SERVER['SCRIPT_FILENAME'] ) === realpath( __FILE__ ) ) {
    http_response_code( 404 );
    exit;
}

/** Fixed public file classes. */
function m2m_content_file_groups() {
    return array(
        'pages'      => array( 'label'=>'Sider og serverkode', 'count'=>0, 'bytes'=>0 ),
        'styles'     => array( 'label'=>'Stil og skript', 'count'=>0, 'bytes'=>0 ),
        'images'     => array( 'label'=>'Bilder og media', 'count'=>0, 'bytes'=>0 ),
        'documents'  => array( 'label'=>'Dokumenter', 'count'=>0, 'bytes'=>0 ),
        'structured' => array( 'label'=>'Strukturerte data', 'count'=>0, 'bytes'=>0 ),
        'archives'   => array( 'label'=>'Arkiver', 'count'=>0, 'bytes'=>0 ),
        'other'      => array( 'label'=>'Andre filer', 'count'=>0, 'bytes'=>0 ),
    );
}

/** Map an extension to one fixed class. */
function m2m_content_file_group( $extension ) {
    $extension = strtolower( (string)$extension );

    if ( in_array( $extension, array( 'html', 'htm', 'php' ), true ) ) {
        return 'pages';
    }
    if ( in_array( $extension, array( 'css', 'js', 'mjs', 'map' ), true ) ) {
        return 'styles';
    }
    if ( in_array( $extension, array( 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'ico', 'avif', 'mp3', 'mp4', 'webm', 'wav' ), true ) ) {
        return 'images';
    }
    if ( in_array( $extension, array( 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods' ), true ) ) {
        return 'documents';
    }
    if ( in_array( $extension, array( 'json', 'jsonl', 'xml', 'csv', 'tsv', 'txt', 'md', 'yaml', 'yml' ), true ) ) {
        return 'structured';
    }
    if ( in_array( $extension, array( 'zip', 'gz', 'tgz', 'bz2', '7z', 'tar' ), true ) ) {
        return 'archives';
    }

    return 'other';
}

/** Walk a fixed tree without following links. */
function m2m_content_files( $root, $limit ) {
    $result = array( 'available'=>false, 'partial'=>false, 'files'=>array() );

    if ( ! is_dir( $root ) || ! is_readable( $root ) ) {
        return $result;
    }

    $result['available'] = true;
    $stack = array( array( rtrim( $root, '/\\' ), 0 ) );
    $skip = array( '.git', '.agent-state', 'logs' );

    while ( count( $stack ) > 0 ) {
        $current = array_pop( $stack );
        $dir = $current[0];
        $depth = $current[1];
        $entries = @scandir( $dir );

        if ( $entries === false ) {
            $result['partial'] = true;
            continue;
        }

        foreach ( $entries as $name ) {
            if ( $name === '.' || $name === '..' ) {
                continue;
            }

            $path = $dir . '/' . $name;

            if ( is_link( $path ) ) {
                continue;
            }

            if ( is_dir( $path ) ) {
                if ( $depth < 12 && substr( $name, 0, 1 ) !== '.' && ! in_array( $name, $skip, true ) ) {
                    $stack[] = array( $path, $depth + 1 );
                }
                continue;
            }

            if ( ! is_file( $path ) || substr( $name, 0, 1 ) === '.' ) {
                continue;
            }

            if ( count( $result['files'] ) >= $limit ) {
                $result['partial'] = true;
                break 2;
            }

            $result['files'][] = $path;
        }
    }

    return $result;
}

/** Does one local web path resolve to a public file in this static layout? */
function m2m_content_internal_target_exists( $root, $source, $target ) {
    $target = html_entity_decode( trim( (string)$target ), ENT_QUOTES, 'UTF-8' );
    $parts = @parse_url( $target );

    if ( $parts === false ) {
        return false;
    }

    $path = isset( $parts['path'] ) ? rawurldecode( (string)$parts['path'] ) : '';

    if ( $path === '' ) {
        return true;
    }

    if ( substr( $path, 0, 1 ) === '/' ) {
        $relative = ltrim( $path, '/' );
    } else {
        $base = str_replace( '\\', '/', dirname( substr( $source, strlen( rtrim( $root, '/\\' ) ) + 1 ) ) );
        $relative = ( $base === '.' ? '' : $base . '/' ) . $path;
    }

    $segments = array();
    foreach ( explode( '/', str_replace( '\\', '/', $relative ) ) as $segment ) {
        if ( $segment === '' || $segment === '.' ) {
            continue;
        }
        if ( $segment === '..' ) {
            if ( count( $segments ) === 0 ) {
                return false;
            }
            array_pop( $segments );
            continue;
        }
        $segments[] = $segment;
    }

    $relative = implode( '/', $segments );
    $base_path = rtrim( $root, '/\\' ) . '/' . $relative;
    $candidates = array( $base_path );

    if ( $relative === '' ) {
        $candidates[] = rtrim( $root, '/\\' ) . '/index.html';
        $candidates[] = rtrim( $root, '/\\' ) . '/index.php';
    } elseif ( pathinfo( $relative, PATHINFO_EXTENSION ) === '' ) {
        $candidates[] = $base_path . '.html';
        $candidates[] = $base_path . '.php';
        $candidates[] = $base_path . '/index.html';
        $candidates[] = $base_path . '/index.php';
    }

    foreach ( $candidates as $candidate ) {
        if ( is_file( $candidate ) && ! is_link( $candidate ) ) {
            return true;
        }
    }

    return false;
}

/** Count links and forms in public markup. Values are hashed or discarded. */
function m2m_content_markup( $root, $host, $files ) {
    $out = array(
        'files_read'=>0,
        'files_skipped'=>0,
        'links'=>0,
        'unique_links'=>0,
        'internal_links'=>0,
        'external_links'=>0,
        'broken_internal_links'=>0,
        'forms'=>0,
        'upload_forms'=>0,
    );
    $unique = array();

    foreach ( $files as $path ) {
        $extension = strtolower( (string)pathinfo( $path, PATHINFO_EXTENSION ) );

        if ( ! in_array( $extension, array( 'html', 'htm', 'php' ), true ) ) {
            continue;
        }

        $size = @filesize( $path );
        if ( $size === false || $size > 2097152 ) {
            $out['files_skipped']++;
            continue;
        }

        $source = @file_get_contents( $path );
        if ( $source === false ) {
            $out['files_skipped']++;
            continue;
        }

        $out['files_read']++;
        $out['forms'] += preg_match_all( '/<form\b/i', $source, $unused );
        $out['upload_forms'] += preg_match_all( '/<input\b[^>]*\btype\s*=\s*(["\x27])file\1/i', $source, $unused );

        preg_match_all( '/<a\b[^>]*\bhref\s*=\s*(["\x27])(.*?)\1/is', $source, $matches );

        foreach ( $matches[2] as $href ) {
            $href = html_entity_decode( trim( (string)$href ), ENT_QUOTES, 'UTF-8' );

            if ( $href === '' || substr( $href, 0, 1 ) === '#'
                 || preg_match( '/^(?:mailto|tel|javascript|data):/i', $href ) ) {
                continue;
            }

            $out['links']++;
            $unique[ hash( 'sha256', $href ) ] = true;
            $parts = @parse_url( $href );
            $link_host = is_array( $parts ) && isset( $parts['host'] ) ? strtolower( (string)$parts['host'] ) : '';
            $own_host = strtolower( (string)$host );
            $internal = $link_host === '' || $link_host === $own_host || $link_host === 'www.' . $own_host;

            if ( ! $internal ) {
                $out['external_links']++;
                continue;
            }

            $out['internal_links']++;
            if ( ! m2m_content_internal_target_exists( $root, $path, $href ) ) {
                $out['broken_internal_links']++;
            }
        }
    }

    $out['unique_links'] = count( $unique );
    return $out;
}

/** Aggregate the processed records published for AI and search crawlers. */
function m2m_content_published( $dir, $now, $retention_days, $limit ) {
    $walk = m2m_content_files( $dir, $limit );
    $out = array(
        'available'=>$walk['available'],
        'partial'=>$walk['partial'],
        'records'=>0,
        'files'=>0,
        'bytes'=>0,
        'oldest'=>null,
        'newest'=>null,
        'expired'=>0,
        'invalid'=>0,
        'token_estimate'=>0,
        'embedding_ready'=>0,
        'content_links'=>0,
        'retention_days'=>(int)$retention_days,
        'types'=>array(
            'article'=>0,
            'tech_article'=>0,
            'faq'=>0,
            'product'=>0,
            'organization'=>0,
            'other'=>0,
        ),
    );

    if ( ! $walk['available'] ) {
        return $out;
    }

    foreach ( $walk['files'] as $path ) {
        $extension = strtolower( (string)pathinfo( $path, PATHINFO_EXTENSION ) );
        if ( ! in_array( $extension, array( 'json', 'md' ), true ) ) {
            continue;
        }

        $size = @filesize( $path );
        $mtime = @filemtime( $path );
        $out['files']++;
        $out['bytes'] += $size === false ? 0 : max( 0, (int)$size );

        if ( $mtime !== false ) {
            $mtime = (int)$mtime;
            $out['oldest'] = $out['oldest'] === null ? $mtime : min( $out['oldest'], $mtime );
            $out['newest'] = $out['newest'] === null ? $mtime : max( $out['newest'], $mtime );
        }

        if ( $extension !== 'json' ) {
            continue;
        }

        $out['records']++;
        if ( $size === false || $size < 1 || $size > 5242880 ) {
            $out['invalid']++;
            continue;
        }

        $raw = @file_get_contents( $path );
        $data = $raw === false ? null : json_decode( $raw, true );
        if ( ! is_array( $data ) ) {
            $out['invalid']++;
            continue;
        }

        $meta = isset( $data['ai_meta'] ) && is_array( $data['ai_meta'] ) ? $data['ai_meta'] : array();
        $content = isset( $data['content'] ) && is_array( $data['content'] ) ? $data['content'] : array();
        $structure = isset( $data['structure'] ) && is_array( $data['structure'] ) ? $data['structure'] : array();

        $out['token_estimate'] += max( 0, (int)( isset( $meta['token_est'] ) ? $meta['token_est'] : 0 ) );
        if ( ! empty( $meta['embedding_ready'] ) ) {
            $out['embedding_ready']++;
        }
        if ( isset( $content['links'] ) && is_array( $content['links'] ) ) {
            $out['content_links'] += count( $content['links'] );
        }

        $expires = isset( $meta['expires'] ) ? strtotime( (string)$meta['expires'] ) : false;
        if ( $expires !== false && $expires <= $now ) {
            $out['expired']++;
        } elseif ( $expires === false && $mtime !== false && $mtime + ( $retention_days * 86400 ) <= $now ) {
            $out['expired']++;
        }

        $raw_type = strtolower( preg_replace( '/[^a-z]/i', '', (string)( isset( $structure['@type'] ) ? $structure['@type'] : '' ) ) );
        $map = array(
            'article'=>'article',
            'newsarticle'=>'article',
            'blogposting'=>'article',
            'techarticle'=>'tech_article',
            'faqpage'=>'faq',
            'product'=>'product',
            'organization'=>'organization',
        );
        $type = isset( $map[ $raw_type ] ) ? $map[ $raw_type ] : 'other';
        $out['types'][ $type ]++;
    }

    return $out;
}

/** Build one aggregate response for a fixed site configuration. */
function m2m_content_inventory( $site, $config, $now ) {
    $root = $config['root'];
    $walk = m2m_content_files( $root, 20000 );
    $groups = m2m_content_file_groups();
    $total_bytes = 0;
    $oldest = null;
    $newest = null;

    foreach ( $walk['files'] as $path ) {
        $bytes = @filesize( $path );
        $mtime = @filemtime( $path );
        $bytes = $bytes === false ? 0 : max( 0, (int)$bytes );
        $group = m2m_content_file_group( pathinfo( $path, PATHINFO_EXTENSION ) );
        $groups[ $group ]['count']++;
        $groups[ $group ]['bytes'] += $bytes;
        $total_bytes += $bytes;

        if ( $mtime !== false ) {
            $mtime = (int)$mtime;
            $oldest = $oldest === null ? $mtime : min( $oldest, $mtime );
            $newest = $newest === null ? $mtime : max( $newest, $mtime );
        }
    }

    $published = null;
    if ( isset( $config['published_dir'] ) ) {
        $published = m2m_content_published(
            $config['published_dir'],
            $now,
            isset( $config['published_retention_days'] ) ? (int)$config['published_retention_days'] : 180,
            20000
        );
    }

    return array(
        'site'=>$site,
        'host'=>$config['host'],
        'generated_at'=>$now,
        'files'=>array(
            'available'=>$walk['available'],
            'partial'=>$walk['partial'],
            'count'=>count( $walk['files'] ),
            'bytes'=>$total_bytes,
            'oldest'=>$oldest,
            'newest'=>$newest,
            'groups'=>$groups,
        ),
        'markup'=>m2m_content_markup( $root, $config['host'], $walk['files'] ),
        'published'=>$published,
    );
}
