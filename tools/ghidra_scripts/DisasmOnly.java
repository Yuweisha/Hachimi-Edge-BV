// Ghidra 脚本：只反汇编指定 RVA 的机器码，不尝试反编译
// 用法: -postScript DisasmOnly.java 0x42990
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Function;
import java.io.*;

public class DisasmOnly extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("用法: DisasmOnly.java <rva_hex> [rva_hex ...]");
            return;
        }

        String outPath = "C:/Users/Schwarz/uma_metadata/disasm_only.txt";
        PrintWriter w = new PrintWriter(new FileWriter(outPath));

        for (String a : args) {
            long rva = Long.parseLong(a.replace("0x", ""), 16);
            Address addr = currentProgram.getImageBase().add(rva);
            w.println("// ==================================================================");
            w.println("// RVA 0x" + Long.toHexString(rva) + "  VA " + addr);
            w.println("// ==================================================================");

            Function f = getFunctionContaining(addr);
            Address start = (f != null) ? f.getEntryPoint() : addr;
            if (f == null) {
                try { disassemble(addr); } catch (Exception e) { }
                start = addr;
            }

            // 先清掉旧指令，强制重新反汇编
            try { clearListing(start, start.add(0x2000)); } catch (Exception e) { }
            try { disassemble(start); } catch (Exception e) {
                w.println("// disassemble 失败: " + e.getMessage());
            }

            Address cur = start;
            int n = 0;
            while (cur != null && n < 2000) {
                Instruction ins = getInstructionAt(cur);
                if (ins == null) {
                    try { disassemble(cur); ins = getInstructionAt(cur); } catch (Exception e) { }
                    if (ins == null) break;
                }
                w.println(cur + "  " + ins.toString());
                cur = ins.getNext();
                n++;
                // 遇到 ret 且后续不是本函数代码则停
                if (ins.getMnemonicString().equalsIgnoreCase("ret")) break;
            }
            w.println();
        }
        w.close();
        println("OUTPUT: " + outPath);
    }
}
