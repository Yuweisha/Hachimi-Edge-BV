// Ghidra 脚本：导出 RaceSimulateDataHeader 相关函数的反编译伪代码
// @category Export
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.PrintWriter;

public class DumpHeader extends GhidraScript {
    @Override
    public void run() throws Exception {
        long[] targets = {
            0x183364e60L,   // RaceSimulateDataHeader..ctor #1
            0x183364e90L,   // RaceSimulateDataHeader..ctor #2
            0x183364c60L,   // RaceSimulateDataHeader.Serialize
            0x183364c30L,   // RaceSimulateDataHeader.Deserialize
            0x183366a90L,   // header 读取 A（Deserialize 里调用）
            0x183366b50L,   // header 读取 B
            0x183366b30L,   // read int（BinaryReader）
            0x18258c8f0L   // Deserialize_Ver20200303_OrNewer（开头看 seed 读取）
        };
        String[] names = {
            "Header_ctor1", "Header_ctor2", "Header_Serialize", "Header_Deserialize",
            "headerReadA", "headerReadB", "readInt", "Deserialize_Main"
        };

        FunctionManager fm = currentProgram.getFunctionManager();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();

        String outPath = "C:/Users/Schwarz/uma_metadata/decompiled_header.c";
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
            DecompileResults res = ifc.decompileFunction(f, 90, mon);
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
