//
//
//
//
//
module mul4 #(
    parameter   WIDTH                   = 4
) (
    input  wire                         opsigned,
    input  wire [WIDTH-1:0]             a,
    input  wire [WIDTH-1:0]             b,
    output wire [WIDTH+WIDTH-1:0]       p
);

    // This was a stub to just check the testbench connectivity
    assign p = opsigned ? {WIDTH{1'b1}} : {WIDTH{1'b0}};

endmodule
