/*
 * Copyright (c) 2023-2024 Darryl L. Miles
 * SPDX-License-Identifier: Apache-2.0
 *
 *  cc -o make_table make_table.c
 */
#include <stdio.h>

static void
emit(const int DD, const int dd) {

    printf("### %x / %x\n", DD, dd);

    {
        const int D = DD;
        const int d = dd;
        printf("### %2d div %2d  =  %2d rem %2d\n", D, d, D / d, D % d);
    }
    {
        const int D = -DD;
        const int d = dd;
        printf("### %2d div %2d  =  %2d rem %2d\n", D, d, D / d, D % d);
    }

    {
        const int D = DD;
        const int d = -dd;
        printf("### %2d div %2d  =  %2d rem %2d\n", D, d, D / d, D % d);
    }

    {
        const int D = -DD;
        const int d = -dd;
        printf("### %2d div %2d  =  %2d rem %2d\n", D, d, D / d, D % d);
    }

}

int
main() {

#if 0
    emit(7, 2);
    emit(1, -8);
    emit(7, -2);

    emit(0x0e, 0xfffffff1);
    emit(14, -15);
    emit(14, 17);
#endif

    emit(1, -31);

    const int is_signed = 1;

    printf("v3.0 hex words addressed\n");

    for(int addr = 0; addr < 0x100; addr += 0x10) {
        printf("%02x:", addr);

        for(int div = 0; div <= 0xf; div++) {
            int D = (addr >> 4) & 0xf;
            int d = div;

            int D_s = D;
            int d_s = d;
            if(D > 0x7)
                D_s = D - 0x10;
            if(d > 0x7)
                d_s = d - 0x10;

            int q;
            int r;
            int q_s;
            int r_s;
            int f_div0;
            if(d != 0) {
                q = D / d;
                r = D % d;
                q_s = D_s / d_s;
                r_s = D_s % d_s;
                f_div0 = 0;
            } else {
                q = 0xf;
                r = 0xf;
                q_s = 0x7;
                r_s = 0x7;
                f_div0 = 1;
            }

            int D_m = D & 0xf;
            int d_m = d & 0xf;
            int q_m = q & 0xf;
            int r_m = r & 0xf;

            int D_sm = D_s & 0xf;
            int d_sm = d_s & 0xf;
            int q_sm = q_s & 0xf;
            int r_sm = r_s & 0xf;

            int value = r_m;
            value |= q_m << 4;
            value |= D_m << 12;
            value |= d_m << 8;

            int value_s = r_sm;
            value_s |= q_sm << 4;
            value_s |= D_sm << 12;
            value_s |= d_sm << 8;
            
            if(is_signed) {
                printf(" %04x", value_s);
            } else {
                printf(" %04x", value);
            }
        }

        printf("\n");
    }

    printf("# D[15:12] / d[11:8] = Q[7:4] R[3:0] signed=%d\n", is_signed);
    printf("\n");

}

