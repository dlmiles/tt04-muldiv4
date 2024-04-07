#!/usr/bin/perl
#
# Copyright (c) 2023-2024 Darryl L. Miles
# SPDX-License-Identifier: Apache-2.0
#

use strict;
use warnings;

printf "v3.0 hex words addressed\n";

my $debug = 0;
$debug = 0 if($ENV{DEBUG} eq '0');
$debug = 1 if($ENV{DEBUG} eq '1');

my $signed = 0;
$signed = 0 if($ENV{SIGNED} eq '0');
$signed = 1 if($ENV{SIGNED} eq '1');

my $addr;
for($addr = 0; $addr < 0x100; $addr = $addr + 0x10) {
    printf "%02x:", $addr;

    my $mul;
    for($mul = 0; $mul <= 0xf; $mul++) {
        my $a = $addr >> 4;
        my $b = $mul;
    
        # signed
        my $a_s = $a;
        my $b_s = $b;
        if($a > 0x7) {
            $a_s = $a - 0x10;
        }
        if($b > 0x7) {
            $b_s = $b - 0x10;
        }

        my $p = $a * $b;
        my $p_s = $a_s * $b_s;

        my $a_m = $a & 0xf;
        my $b_m = $b & 0xf;
        my $p_m = $p & 0xff;

        my $a_sm = $a_s & 0xf;
        my $b_sm = $b_s & 0xf;
        my $p_sm = $p_s & 0xff;

        my $value = $p_m;
        $value |= $a_m << 12;
        $value |= $b_m << 8;

        my $value_s = $p_sm;
        $value_s |= $a_sm << 12;
        $value_s |= $b_sm << 8;

        if($signed) {
            printf " %04x", $value_s;
        } else {
            printf " %04x", $value;
        }
        my $s = '';
        if($p_m == $p_sm) {
            $s = ' ';
        } elsif($p_m == (~$p_sm)) {
            $s = '~' ;
        } elsif($p_m == (-$p_sm)) {
            $s = '-';
        } else {  # if($p_m != $p_sm)
            $s = '*';
        }
        printf "%s", $s if($debug);

        if($signed) {
            printf STDERR "A = %4d (%01x)   B = %4d (%01x)    P = %5d (%02x)  %s (%02x)\n", $a_s, $a_sm, $b_s, $b_sm, $p_s, $p_sm, $s, $p_m;
        } else {
            printf STDERR "A = %4d (%01x)   B = %4d (%01x)    P = %5d (%02x)  %s (%02x)\n", $a, $a_m, $b, $b_m, $p, $p_m, $s, $p_sm;
        }
    }

    printf "\n";
}

printf "# A[15:12] * B[11:8] = P[7:0] signed=$signed\n";
printf "\n";

printf STDERR "# A[15:12] * B[11:8] = P[7:0] signed=$signed\n";
