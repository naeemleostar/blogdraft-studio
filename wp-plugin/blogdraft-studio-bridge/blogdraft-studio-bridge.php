<?php
/**
 * Plugin Name: BlogDraft Studio Bridge
 * Description: Lets the BlogDraft Studio desktop app fill the SEO title, meta description and focus keyword of Yoast SEO or Rank Math through the REST API. Only logged-in users who can edit posts can write these fields.
 * Version: 2.0.0
 * License: GPL-2.0-or-later
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_action( 'init', function () {
	$keys = array(
		'_yoast_wpseo_title', '_yoast_wpseo_metadesc', '_yoast_wpseo_focuskw',
		'rank_math_title', 'rank_math_description', 'rank_math_focus_keyword',
	);
	foreach ( $keys as $key ) {
		register_post_meta(
			'post',
			$key,
			array(
				'type'              => 'string',
				'single'            => true,
				'show_in_rest'      => true,
				'sanitize_callback' => 'sanitize_text_field',
				'auth_callback'     => function () {
					return current_user_can( 'edit_posts' );
				},
			)
		);
	}
} );

add_action( 'rest_api_init', function () {
	register_rest_route(
		'blogdraft-studio/v1',
		'/ping',
		array(
			'methods'             => 'GET',
			'permission_callback' => '__return_true',
			'callback'            => function () {
				return array(
					'ok'       => true,
					'version'  => '2.0.0',
					'yoast'    => defined( 'WPSEO_VERSION' ),
					'rankmath' => class_exists( 'RankMath' ),
				);
			},
		)
	);
} );
