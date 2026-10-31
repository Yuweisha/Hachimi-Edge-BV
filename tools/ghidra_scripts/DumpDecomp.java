// Ghidra 脚本：导出指定地址的反编译伪代码
// @category Export
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.PrintWriter;

public class DumpDecomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        long[] targets = {
            0x183e65b90L,   // CacheHorseFinishOrder
            0x183e660e0L,   // DecidePlayerHorseIndexByFinishOrder
            0x183e66c60L,   // GetPlayerHorseFinishOrder
            0x183d0f0e0L,   // RaceHorseManagerBase.CalcHorseOrder
            0x183ed01c0L,   // rank array builder
            0x18258db50L,   // RaceSimulateData.GetResult1
            0x18258daf0L,   // RaceSimulateData.GetResult2
            0x18258d870L,   // GetHorseResultData
            0x183e02ce0L,   // unknown A
            0x183e02a90L    // unknown B
        };
        String[] names = {
            "CacheHorseFinishOrder", "DecidePlayerHorseIndexByFinishOrder",
            "GetPlayerHorseFinishOrder", "RaceHorseManagerBase_CalcHorseOrder",
            "rank_array_builder", "GetResult1", "GetResult2", "GetHorseResultData",
            "unknownA", "unknownB"
        };

        FunctionManager fm = currentProgram.getFunctionManager();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();

        String outPath = "C:/Users/Schwarz/uma_metadata/decompiled_targets.c";
        PrintWriter pw = new PrintWriter(outPath, "UTF-8");

        for (int i = 0; i < targets.length; i++) {
            Address addr = toAddr(targets[i]);
            Function f = fm.getFunctionContaining(addr);
            pw.println();
            pw.println("// " + "=".repeat(76));
            pw.println("// " + names[i] + "  @ 0x" + Long.toHexString(targets[i]));
            if (f == null) {
                pw.println("// （该地址不在任何函数内）");
                println(names[i] + ": 无函数");
                continue;
            }
            pw.println("// 函数: " + f.getName() + "  入口 0x" + f.getEntryPoint());
            DecompileResults res = ifc.decompileFunction(f, 90, mon);
            if (res == null || !res.decompileCompleted()) {
                pw.println("// 反编译失败");
                println(names[i] + ": 失败");
                continue;
            }
            pw.println(res.getDecompiledFunction().getC());
            println(names[i] + ": OK (" + f.getName() + ")");
        }
        pw.close();
        println("输出: " + outPath);
    }
}
