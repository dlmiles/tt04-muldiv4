//
//
//
//
//
module div4 #(
    parameter   WIDTH                   = 4
) (
    input  wire                         opsigned,
    input  wire [WIDTH-1:0]             dividend,
    input  wire [WIDTH-1:0]             divisor,
    output wire [WIDTH-1:0]             quotient,
    output wire [WIDTH-1:0]             remainder,
    output wire                         ediv0,
    output wire                         eover
);

    // This was a stub to just check the testbench connectivity
    assign quotent   = opsigned ? {WIDTH{1'b1}} : {WIDTH{1'b0}};
    assign remainder = opsigned ? {WIDTH{1'b1}} : {WIDTH{1'b0}};
    assign ediv0 = ~dividend[0];
    assign eover = ~divisor[1];

endmodule
