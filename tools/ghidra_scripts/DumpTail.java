// Ghidra 脚本：导出尾部解析相关函数
// @category Export
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.PrintWriter;

public class DumpTail extends GhidraScript {
    @Override
    public void run() throws Exception {
        long[] targets = {
            0x183364ed0L,   // 尾部记录解析（Deserialize 里调用）
            0x1833655d0L,   // 尾部记录构造
            0x183364c30L,   // Header.Deserialize
            0x183366b10L,   // readShort
            0x1833659d0L,   // 帧数据解析
            0x183366420L,   // 结果块解析入口（版本分支）
            0x1833661a0L,   // 结果块解析基础
            0x183365fc0L    // 结果块解析（新版）
        };
        String[] names = {
            "TailRecordParse", "TailRecordCtor", "HeaderDeserialize", "readShort",
            "FrameParse", "ResultParseEntry", "ResultParseBase", "ResultParseNew"
        };

        FunctionManager fm = currentProgram.getFunctionManager();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();

        String outPath = "C:/Users/Schwarz/uma_metadata/decompiled_tail.c";
        PrintWriter pw = new PrintWriter(outPath, "UTF-8");

        for (int i = 0; i < targets.length; i++) {
            Address addr = toAddr(targets[i]);
            Function f = fm.getFunctionContaining(addr);
            pw.println();
            pw.println("// ========================================================================");
            pw.println("// " + names[i] + "  @ 0x" + Long.toHexString(targets[i]));
            if (f == null) {
                pw.println("// (no function)");
                println(names[i] + ": no function");
                continue;
            }
            pw.println("// function: " + f.getName() + "  entry 0x" + f.getEntryPoint());
            DecompileResults res = ifc.decompileFunction(f, 120, mon);
            if (res == null || !res.decompileCompleted()) {
                pw.println("// decompile failed");
                println(names[i] + ": FAILED");
                continue;
            }
            pw.println(res.getDecompiledFunction().getC());
            println(names[i] + ": OK");
        }
        pw.close();
        println("OUTPUT: " + outPath);
    }
}
