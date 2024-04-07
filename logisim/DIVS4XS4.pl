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

my $signed = 1;
$signed = 0 if($ENV{SIGNED} eq '0');
$signed = 1 if($ENV{SIGNED} eq '1');

my $addr;
for($addr = 0; $addr < 0x100; $addr = $addr + 0x10) {
    printf "%02x:", $addr;

    my $div;
    for($div = 0; $div <= 0xf; $div++) {
        my $a = $addr >> 4;
        my $b = $div;
    
        # signed
        my $a_s = $a;
        my $b_s = $b;
        if($a > 0x7) {
            $a_s = $a - 0x10;
        }
        if($b > 0x7) {
            $b_s = $b - 0x10;
        }

        my $q;
        my $r;
        my $q_s;
        my $r_s;
        my $f_div0;
        if($b != 0) {
            $q = $a / $b;
            $r = $a % $b;
            $q_s = $a_s / $b_s;
            $r_s = $a_s % $b_s;
            # Weird Perl has difference signs to C here
            #                             Perl       C
            #  7 div  2 =  3    1        3 r  1    3 r  1   good
            # -7 div  2 = -3 r -1       -3 r  1   -3 r -1   bad
            #  7 div -2 = -3 r  1       -3 r -1   -3 r  1   bad
            # -7 div -2 =  3 r -1        3 r -1    3 r -1   good
            if($a_s < 0 && $b_s >= 0) {
                $r_s = -$r_s;
            } elsif($a_s >= 0 && $b_s < 0) {
                $r_s = -$r_s;
            } $f_div0 = 0;
        } else {
            $q = 0xf;
            $r = 0xf;
            $q_s = 0x7;
            $r_s = 0x7;
            $f_div0 = 1;
        }

        my $a_m = $a & 0xf;
        my $b_m = $b & 0xf;
        my $q_m = $q & 0xf;
        my $r_m = $r & 0xf;

        my $a_sm = $a_s & 0xf;
        my $b_sm = $b_s & 0xf;
        my $q_sm = $q_s & 0xf;
        my $r_sm = $r_s & 0xf;

        my $value = $r_m;
        $value |= $q_m << 4;
        $value |= $a_m << 12;
        $value |= $b_m << 8;

        my $value_s = $r_sm;
        $value_s |= $q_sm << 4;
        $value_s |= $a_sm << 12;
        $value_s |= $b_sm << 8;

        if($signed) {
            printf " %04x", $value_s;
        } else {
            printf " %04x", $value;
        }
        my $s = '';
        if($q_m == $q_sm) {
            $s = ' ';
        } elsif($q_m == (~$q_sm)) {
            $s = '~' ;
        } elsif($q_m == (-$q_sm)) {
            $s = '-';
        } else {  # if($q_m != $q_sm)
            $s = '*';
        }
        printf "%s", $s if($debug);
        my $s_div0 = '    ';
        $s_div0 = 'DIV0' if($f_div0);

        if($signed) {
            printf STDERR "D = %4d (%01x)   d = %4d (%01x)    Q = %5d (%01x)  R = %5d (%01x)  %s  %s (%01x r %01x)\n", $a_s, $a_sm, $b_s, $b_sm, $q_s, $q_sm, $r_s, $r_sm, $s_div0, $s, $q_m, $r_m;
        } else {
            printf STDERR "D = %4d (%01x)   d = %4d (%01x)    Q = %5d (%01x)  R = %5d (%01x)  %s  %s (%01x r %01x)\n", $a, $a_m, $b, $b_m, $q, $q_m, $r, $r_m, $s_div0, $s, $q_sm, $r_sm;
        }
    }

    printf "\n";
}

printf "# D[15:12] / d[11:8] = Q[7:4] R[3:0] signed=$signed\n";
printf "\n";

printf STDERR "# D[15:12] / d[11:8] = Q[7:4] R[3:0] signed=$signed\n";
