// Ghidra 脚本：反汇编指定 RVA 的一批地址，输出伪代码 + 汇编
// 用法: -postScript DisasRanges.java 0x3d03bd0 0x3d05830 ...
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import java.io.*;
import java.util.*;

public class DisasRanges extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("用法: DisasRanges.java <rva_hex> [rva_hex ...]");
            return;
        }

        String outPath = "C:/Users/Schwarz/uma_metadata/disas_out.txt";
        PrintWriter w = new PrintWriter(new FileWriter(outPath));

        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);

        for (String a : args) {
            long rva = Long.parseLong(a.replace("0x", ""), 16);
            Address addr = currentProgram.getImageBase().add(rva);
            w.println("// ==================================================================");
            w.println("// RVA 0x" + Long.toHexString(rva) + "  VA " + addr);
            w.println("// ==================================================================");
            w.println();

            // 先看看这里有没有现成函数
            Function f = getFunctionAt(addr);
            if (f == null) {
                f = getFunctionContaining(addr);
            }
            if (f != null) {
                w.println("// 已有函数: " + f.getName() + " @ " + f.getEntryPoint());
                DecompileResults res = ifc.decompileFunction(f, 60, monitor);
                if (res != null && res.decompileCompleted()) {
                    w.println(res.getDecompiledFunction().getC());
                } else {
                    w.println("// 反编译失败");
                }
            } else {
                w.println("// 没有现成函数，直接反汇编机器码");
                // 创建函数
                try {
                    disassemble(addr);
                    createFunction(addr, null);
                    Function nf = getFunctionAt(addr);
                    if (nf != null) {
                        w.println("// 新建函数: " + nf.getName());
                        DecompileResults res = ifc.decompileFunction(nf, 60, monitor);
                        if (res != null && res.decompileCompleted()) {
                            w.println(res.getDecompiledFunction().getC());
                        }
                    }
                } catch (Exception e) {
                    w.println("// 创建函数失败: " + e.getMessage());
                }
                // 无论如何都打原始汇编
                w.println("// ---- 原始反汇编 ----");
                Address cur = addr;
                for (int i = 0; i < 80; i++) {
                    Instruction insn = getInstructionAt(cur);
                    if (insn == null) {
                        disassemble(cur);
                        insn = getInstructionAt(cur);
                        if (insn == null) break;
                    }
                    w.println(cur + "  " + insn.toString());
                    cur = insn.getNext().getAddress();
                    if (insn.getMnemonicString().equals("RET")) break;
                }
            }
            w.println();
        }
        w.close();
        ifc.dispose();
        println("OUTPUT: " + outPath);
    }
}
