// FUN_7ffa1b03ed20 @ 0x7ffa1b03ed20
// signature: undefined FUN_7ffa1b03ed20()
// ==================================================================

/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */

int FUN_7ffa1b03ed20(longlong param_1,longlong param_2,longlong *param_3,undefined8 param_4,
                    longlong param_5,undefined8 param_6)

{
  int iVar1;
  longlong lVar2;
  ulonglong uVar3;
  byte bVar4;
  undefined1 *puVar5;
  undefined1 auStack_118 [32];
  undefined1 **local_f8;
  undefined1 **local_f0;
  undefined1 **local_e8;
  undefined1 *local_d8;
  undefined4 local_d0;
  undefined1 *local_c8;
  undefined4 local_c0;
  undefined1 *local_b8;
  undefined4 local_b0;
  undefined1 *local_a8;
  undefined4 local_a0;
  undefined8 local_98;
  undefined1 *local_88;
  undefined4 local_80;
  undefined1 *local_78;
  undefined4 local_70;
  undefined1 *local_68;
  undefined4 local_60;
  undefined1 *local_58;
  undefined4 local_50;
  ulonglong local_48;
  
  local_48 = DAT_7ffa1b381040 ^ (ulonglong)auStack_118;
  local_98 = param_6;
  local_d0 = 1;
  local_d8 = (undefined1 *)0x0;
  local_c0 = 1;
  local_c8 = (undefined1 *)0x0;
  local_b0 = 1;
  local_b8 = (undefined1 *)0x0;
  local_a0 = 1;
  local_a8 = (undefined1 *)0x0;
  local_80 = 1;
  local_88 = (undefined1 *)0x0;
  local_70 = 1;
  local_78 = (undefined1 *)0x0;
  local_60 = 1;
  local_68 = (undefined1 *)0x0;
  local_50 = 1;
  local_58 = (undefined1 *)0x0;
  if (param_5 == 0) {
    iVar1 = -0x4f80;
  }
  else {
    iVar1 = FUN_7ffa1b045c10(&local_a8,param_4);
    if ((((iVar1 == 0) && (iVar1 = FUN_7ffa1b039390(&local_d8,param_4), iVar1 == 0)) &&
        (iVar1 = FUN_7ffa1b045d10(param_2,1), iVar1 == 0)) &&
       (iVar1 = FUN_7ffa1b045d10(param_2 + 0x20,0), iVar1 == 0)) {
      FUN_7ffa1b0458a0(param_2 + 0x10);
      iVar1 = FUN_7ffa1b046600(&local_d8,param_1 + 8);
      while (-1 < iVar1) {
        iVar1 = FUN_7ffa1b046830(&local_d8,&local_d8,param_1 + 8);
        if (iVar1 != 0) goto LAB_7ffa1b03ef8c;
        iVar1 = FUN_7ffa1b046600(&local_d8,param_1 + 8);
      }
      iVar1 = FUN_7ffa1b03e5e0(param_1,&local_d8,param_5,local_98);
      if (iVar1 == 0) {
        uVar3 = *(longlong *)(param_1 + 0x80) + 1;
        while (uVar3 != 0) {
          uVar3 = uVar3 - 1;
          if (uVar3 < (ulonglong)*(ushort *)((longlong)param_3 + 10) * 0x40) {
            bVar4 = (byte)(*(ulonglong *)(*param_3 + (uVar3 >> 6) * 8) >> ((byte)uVar3 & 0x3f)) & 1;
          }
          else {
            bVar4 = 0;
          }
          iVar1 = FUN_7ffa1b0457a0(param_2,&local_d8,bVar4);
          if ((iVar1 != 0) || (iVar1 = FUN_7ffa1b0457a0(param_2 + 0x20,&local_b8,bVar4), iVar1 != 0)
             ) goto LAB_7ffa1b03ef8c;
          local_e8 = &local_88;
          local_f0 = &local_a8;
          local_f8 = &local_d8;
          iVar1 = FUN_7ffa1b03e970(param_1,param_2,&local_d8,param_2);
          if ((iVar1 != 0) ||
             ((iVar1 = FUN_7ffa1b0457a0(param_2,&local_d8,bVar4), iVar1 != 0 ||
              (iVar1 = FUN_7ffa1b0457a0(param_2 + 0x20,&local_b8,bVar4), iVar1 != 0))))
          goto LAB_7ffa1b03ef8c;
        }
        iVar1 = FUN_7ffa1b03e440(param_1,param_2);
      }
    }
LAB_7ffa1b03ef8c:
    if (local_d8 != (undefined1 *)0x0) {
      lVar2 = (ulonglong)local_d0._2_2_ << 3;
      if ((ulonglong)local_d0._2_2_ != 0) {
        puVar5 = local_d8;
        for (; lVar2 != 0; lVar2 = lVar2 + -1) {
          *puVar5 = 0;
          puVar5 = puVar5 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(local_d8);
    }
    local_d0 = 1;
    local_d8 = (undefined1 *)0x0;
    if (local_c8 != (undefined1 *)0x0) {
      lVar2 = (ulonglong)local_c0._2_2_ << 3;
      if ((ulonglong)local_c0._2_2_ != 0) {
        puVar5 = local_c8;
        for (; lVar2 != 0; lVar2 = lVar2 + -1) {
          *puVar5 = 0;
          puVar5 = puVar5 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(local_c8);
    }
    local_c0 = 1;
    local_c8 = (undefined1 *)0x0;
    if (local_b8 != (undefined1 *)0x0) {
      lVar2 = (ulonglong)local_b0._2_2_ << 3;
      if ((ulonglong)local_b0._2_2_ != 0) {
        puVar5 = local_b8;
        for (; lVar2 != 0; lVar2 = lVar2 + -1) {
          *puVar5 = 0;
          puVar5 = puVar5 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(local_b8);
    }
    local_b0 = 1;
    local_b8 = (undefined1 *)0x0;
    if (local_a8 != (undefined1 *)0x0) {
      lVar2 = (ulonglong)local_a0._2_2_ << 3;
      if ((ulonglong)local_a0._2_2_ != 0) {
        puVar5 = local_a8;
        for (; lVar2 != 0; lVar2 = lVar2 + -1) {
          *puVar5 = 0;
          puVar5 = puVar5 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(local_a8);
    }
    if (local_88 != (undefined1 *)0x0) {
      lVar2 = (ulonglong)local_80._2_2_ << 3;
      if ((ulonglong)local_80._2_2_ != 0) {
        puVar5 = local_88;
        for (; lVar2 != 0; lVar2 = lVar2 + -1) {
          *puVar5 = 0;
          puVar5 = puVar5 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(local_88);
    }
    local_80 = 1;
    local_88 = (undefined1 *)0x0;
    if (local_78 != (undefined1 *)0x0) {
      lVar2 = (ulonglong)local_70._2_2_ << 3;
      if ((ulonglong)local_70._2_2_ != 0) {
        puVar5 = local_78;
        for (; lVar2 != 0; lVar2 = lVar2 + -1) {
          *puVar5 = 0;
          puVar5 = puVar5 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(local_78);
    }
    local_70 = 1;
    local_78 = (undefined1 *)0x0;
    if (local_68 != (undefined1 *)0x0) {
      lVar2 = (ulonglong)local_60._2_2_ << 3;
      if ((ulonglong)local_60._2_2_ != 0) {
        puVar5 = local_68;
        for (; lVar2 != 0; lVar2 = lVar2 + -1) {
          *puVar5 = 0;
          puVar5 = puVar5 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(local_68);
    }
    local_60 = 1;
    local_68 = (undefined1 *)0x0;
    if (local_58 != (undefined1 *)0x0) {
      lVar2 = (ulonglong)local_50._2_2_ << 3;
      if ((ulonglong)local_50._2_2_ != 0) {
        puVar5 = local_58;
        for (; lVar2 != 0; lVar2 = lVar2 + -1) {
          *puVar5 = 0;
          puVar5 = puVar5 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(local_58);
    }
  }
  return iVar1;
}



// ==================================================================

// FUN_7ffa1b03e5e0 @ 0x7ffa1b03e5e0
// signature: undefined FUN_7ffa1b03e5e0()
// ==================================================================

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int FUN_7ffa1b03e5e0(longlong param_1,longlong param_2,undefined8 param_3,undefined8 param_4)

{
  ushort uVar1;
  code *pcVar2;
  ushort uVar3;
  int iVar4;
  int iVar5;
  undefined1 *puVar6;
  ulonglong uVar7;
  longlong lVar8;
  undefined1 *puVar9;
  undefined8 local_res8;
  undefined1 *local_48;
  undefined4 local_40;
  undefined8 *local_38;
  undefined4 local_30;
  
  local_40 = 1;
  local_res8 = 2;
  local_48 = (undefined1 *)0x0;
  puVar9 = (undefined1 *)0x0;
  local_30 = 0x10001;
  local_38 = &local_res8;
  iVar4 = FUN_7ffa1b046600(param_1 + 8,&local_38);
  if (iVar4 < 1) {
    iVar4 = -4;
    goto LAB_7ffa1b03e91f;
  }
  uVar1 = *(ushort *)(param_1 + 0x12);
  puVar6 = puVar9;
  if (uVar1 == 0) {
    uVar3 = 0;
  }
  else {
    if (10000 < uVar1) {
      iVar4 = -0x10;
      goto LAB_7ffa1b03e91f;
    }
    uVar3 = 0;
    if (uVar1 != 0) {
      puVar6 = (undefined1 *)_calloc_base(uVar1,8);
      if (puVar6 == (undefined1 *)0x0) {
        iVar4 = -0x10;
        goto LAB_7ffa1b03e91f;
      }
      local_40 = CONCAT22(uVar1,(undefined2)local_40);
      uVar3 = uVar1;
      local_48 = puVar6;
    }
  }
  iVar4 = FUN_7ffa1b075720(puVar6,2,*(undefined8 *)(param_1 + 8),uVar3,param_3,param_4);
  puVar9 = puVar6;
  if ((iVar4 != 0) || (iVar4 = FUN_7ffa1b046d10(param_2,param_2,&local_48), iVar4 != 0))
  goto LAB_7ffa1b03e91f;
  pcVar2 = *(code **)(param_1 + 0x90);
  if (pcVar2 == (code *)0x0) {
    iVar4 = FUN_7ffa1b048740(param_2,param_2,param_1 + 8);
LAB_7ffa1b03e7e5:
    if (iVar4 != 0) goto LAB_7ffa1b03e91f;
    _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
    lVar8 = param_2 + 0x20;
    iVar4 = FUN_7ffa1b046d10(lVar8,lVar8,&local_48);
    if (iVar4 != 0) goto LAB_7ffa1b03e91f;
    pcVar2 = *(code **)(param_1 + 0x90);
    if (pcVar2 == (code *)0x0) {
      iVar4 = FUN_7ffa1b048740(lVar8,lVar8,param_1 + 8);
    }
    else {
      if (*(short *)(param_2 + 0x28) < 0) {
        local_38 = &local_res8;
        local_res8 = 0;
        local_30 = 0x10001;
        iVar4 = FUN_7ffa1b046600(lVar8,&local_38);
        if (iVar4 != 0) goto LAB_7ffa1b03e74b;
      }
      uVar7 = FUN_7ffa1b045fd0(lVar8);
      if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar7) {
        iVar4 = -0x4f80;
        goto LAB_7ffa1b03e91f;
      }
      iVar4 = (*pcVar2)(lVar8);
      if (iVar4 == 0) {
        if (*(short *)(param_2 + 0x28) < 0) {
          local_res8 = 0;
          do {
            local_38 = &local_res8;
            local_30 = 0x10001;
            iVar5 = FUN_7ffa1b046600(lVar8,&local_38);
            if (iVar5 == 0) break;
            iVar4 = FUN_7ffa1b0469c0(lVar8,lVar8,param_1 + 8,1);
            if (iVar4 != 0) goto LAB_7ffa1b03e915;
          } while (*(short *)(param_2 + 0x28) < 0);
        }
        iVar5 = FUN_7ffa1b046600(lVar8,param_1 + 8);
        while ((-1 < iVar5 && (iVar4 = FUN_7ffa1b046830(lVar8,lVar8,param_1 + 8), iVar4 == 0))) {
          iVar5 = FUN_7ffa1b046600(lVar8,param_1 + 8);
        }
      }
    }
LAB_7ffa1b03e915:
    if (iVar4 == 0) {
      _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
    }
  }
  else {
    if (*(short *)(param_2 + 8) < 0) {
      local_38 = &local_res8;
      local_res8 = 0;
      local_30 = 0x10001;
      iVar4 = FUN_7ffa1b046600(param_2,&local_38);
      if (iVar4 == 0) goto LAB_7ffa1b03e737;
    }
    else {
LAB_7ffa1b03e737:
      uVar7 = FUN_7ffa1b045fd0(param_2);
      if (uVar7 <= (ulonglong)(*(longlong *)(param_1 + 0x78) * 2)) {
        iVar4 = (*pcVar2)(param_2);
        if (iVar4 == 0) {
          if (*(short *)(param_2 + 8) < 0) {
            local_res8 = 0;
            do {
              local_38 = &local_res8;
              local_30 = 0x10001;
              iVar5 = FUN_7ffa1b046600(param_2,&local_38);
              if (iVar5 == 0) break;
              iVar4 = FUN_7ffa1b0469c0(param_2,param_2,param_1 + 8,1);
              if (iVar4 != 0) goto LAB_7ffa1b03e7e5;
            } while (*(short *)(param_2 + 8) < 0);
          }
          iVar5 = FUN_7ffa1b046600(param_2,param_1 + 8);
          while ((-1 < iVar5 && (iVar4 = FUN_7ffa1b046830(param_2,param_2,param_1 + 8), iVar4 == 0))
                ) {
            iVar5 = FUN_7ffa1b046600(param_2,param_1 + 8);
          }
        }
        goto LAB_7ffa1b03e7e5;
      }
    }
LAB_7ffa1b03e74b:
    iVar4 = -0x4f80;
  }
LAB_7ffa1b03e91f:
  if (puVar9 != (undefined1 *)0x0) {
    lVar8 = (ulonglong)local_40._2_2_ << 3;
    if ((ulonglong)local_40._2_2_ != 0) {
      puVar6 = puVar9;
      for (; lVar8 != 0; lVar8 = lVar8 + -1) {
        *puVar6 = 0;
        puVar6 = puVar6 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar9);
  }
  if (iVar4 == -0xe) {
    iVar4 = -0x4d00;
  }
  return iVar4;
}



// ==================================================================

// FUN_7ffa1b03e180 @ 0x7ffa1b03e180
// signature: undefined FUN_7ffa1b03e180()
// ==================================================================

/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */

int FUN_7ffa1b03e180(longlong param_1,undefined8 param_2,undefined8 param_3,longlong param_4,
                    undefined8 param_5,undefined8 param_6)

{
  bool bVar1;
  undefined1 *puVar2;
  bool bVar3;
  int iVar4;
  longlong lVar5;
  longlong lVar6;
  byte bVar7;
  longlong lVar8;
  ulonglong uVar9;
  byte bVar10;
  undefined1 auStack_1e8 [32];
  undefined1 *local_1c8;
  undefined1 *local_1c0;
  undefined8 local_1b8;
  undefined8 local_1b0;
  undefined1 local_198 [8];
  undefined1 *local_190;
  longlong local_188;
  undefined8 local_180;
  undefined8 local_178;
  undefined8 local_170;
  undefined1 local_168 [272];
  ulonglong local_58;
  
  local_58 = DAT_7ffa1b381040 ^ (ulonglong)auStack_1e8;
  local_170 = param_5;
  local_178 = param_6;
  local_188 = param_4;
  local_180 = param_3;
  iVar4 = FUN_7ffa1b046600(param_4 + 0x10,param_1 + 0x48);
  if ((iVar4 == 0) && (iVar4 = FUN_7ffa1b046600(param_4,param_1 + 0x38), iVar4 == 0)) {
    uVar9 = *(ulonglong *)(param_1 + 0x80);
    bVar1 = true;
    bVar7 = (0x17f < uVar9) + 5;
    bVar3 = true;
    if ((*(longlong *)(param_1 + 0xb0) == 0) || (*(longlong *)(param_1 + 0xb8) != 0))
    goto LAB_7ffa1b03e23a;
  }
  else {
    uVar9 = *(ulonglong *)(param_1 + 0x80);
    bVar7 = (0x17f < uVar9) + 4;
    bVar3 = false;
LAB_7ffa1b03e23a:
    bVar1 = bVar3;
    if (4 < bVar7) {
      bVar7 = 4;
    }
  }
  if (uVar9 <= bVar7) {
    bVar7 = 2;
  }
  lVar8 = 0;
  bVar10 = '\x01' << (bVar7 - 1 & 0x1f);
  local_190 = (undefined1 *)(((uVar9 - 1) + (ulonglong)bVar7) / (ulonglong)bVar7);
  if ((!bVar1) || (lVar5 = *(longlong *)(param_1 + 0xb0), lVar5 == 0)) {
    uVar9 = (ulonglong)bVar10;
    lVar5 = _calloc_base(uVar9,0x30);
    if (lVar5 == 0) {
      iVar4 = -0x4d80;
      goto LAB_7ffa1b03e3ce;
    }
    if (bVar10 != 0) {
      lVar6 = lVar5 + 10;
      do {
        *(undefined4 *)(lVar6 + -2) = 1;
        *(undefined8 *)(lVar6 + -10) = 0;
        *(undefined4 *)(lVar6 + 0xe) = 1;
        *(undefined8 *)(lVar6 + 6) = 0;
        *(undefined4 *)(lVar6 + 0x1e) = 1;
        *(undefined8 *)(lVar6 + 0x16) = 0;
        lVar6 = lVar6 + 0x30;
        uVar9 = uVar9 - 1;
      } while (uVar9 != 0);
    }
    local_1c8 = local_190;
    iVar4 = FUN_7ffa1b03ceb0(param_1,lVar5,local_188,bVar7);
    if (iVar4 != 0) goto LAB_7ffa1b03e3ce;
    if (bVar1) {
      *(ulonglong *)(param_1 + 0xb8) = (ulonglong)bVar10;
      *(longlong *)(param_1 + 0xb0) = lVar5;
    }
  }
  puVar2 = local_190;
  local_1c0 = local_198;
  local_1c8 = (undefined1 *)CONCAT71(local_1c8._1_7_,bVar7);
  iVar4 = FUN_7ffa1b03dce0(param_1,local_180,local_168,local_190);
  if (iVar4 == 0) {
    local_1b0 = local_178;
    local_1b8 = local_170;
    local_1c8 = local_168;
    local_1c0 = puVar2;
    iVar4 = FUN_7ffa1b03d2e0(param_1,param_2,lVar5,bVar10);
    if ((iVar4 == 0) && (iVar4 = FUN_7ffa1b03bbc0(param_1,param_2,local_198[0]), iVar4 == 0)) {
      iVar4 = FUN_7ffa1b03a610(param_1,param_2);
    }
  }
LAB_7ffa1b03e3ce:
  lVar6 = 0;
  if (lVar5 != *(longlong *)(param_1 + 0xb0)) {
    lVar6 = lVar5;
  }
  if (lVar6 != 0) {
    if (bVar10 != 0) {
      uVar9 = (ulonglong)bVar10;
      do {
        FUN_7ffa1b039080(lVar8 + lVar6);
        lVar8 = lVar8 + 0x30;
        uVar9 = uVar9 - 1;
      } while (uVar9 != 0);
    }
    thunk_FUN_7ffa1b0c8950(lVar6);
  }
  if (iVar4 != 0) {
    FUN_7ffa1b039080(param_2);
  }
  return iVar4;
}



// ==================================================================

// FUN_7ffa1b075720 @ 0x7ffa1b075720
// signature: undefined FUN_7ffa1b075720()
// ==================================================================

ulonglong FUN_7ffa1b075720(ulonglong *param_1,ulonglong param_2,longlong param_3,ulonglong param_4,
                          undefined8 param_5,undefined8 param_6)

{
  ulonglong *puVar1;
  longlong lVar2;
  ulonglong uVar3;
  ulonglong uVar4;
  ulonglong uVar5;
  ulonglong uVar6;
  ulonglong uVar7;
  int iVar8;
  ulonglong uVar9;
  
  iVar8 = (int)param_4 + -1;
  lVar2 = (longlong)iVar8;
  if (-1 < iVar8) {
    do {
      if (*(longlong *)(param_3 + lVar2 * 8) != 0) {
        uVar3 = 0x8000000000000000;
        uVar6 = 0;
        goto LAB_7ffa1b0758f5;
      }
      iVar8 = iVar8 + -1;
      lVar2 = lVar2 + -1;
    } while (-1 < lVar2);
  }
  lVar2 = 0;
  goto LAB_7ffa1b075779;
  while( true ) {
    uVar3 = uVar3 >> 1;
    uVar6 = uVar6 + 1;
    if (0x3f < uVar6) break;
LAB_7ffa1b0758f5:
    if ((uVar3 & *(ulonglong *)(param_3 + (longlong)iVar8 * 8)) != 0) break;
  }
  lVar2 = ((longlong)iVar8 + 1) * 0x40 - uVar6;
LAB_7ffa1b075779:
  uVar6 = lVar2 + 7U >> 3;
  iVar8 = 0xfa;
  if (4 < uVar6) {
    iVar8 = 0x1e;
  }
  while( true ) {
    uVar3 = FUN_7ffa1b075620(param_1,param_4,uVar6,param_5,param_6);
    if ((int)uVar3 != 0) {
      return uVar3;
    }
    FUN_7ffa1b074c60(param_1,param_4,uVar6 * 8 - lVar2);
    iVar8 = iVar8 + -1;
    if (iVar8 == 0) break;
    uVar7 = DAT_7ffa1b398920 ^ param_2;
    uVar5 = (longlong)
            (-(DAT_7ffa1b398920 >> 1) |
            -((uVar7 ^ DAT_7ffa1b398920 ^ *param_1) >> 0x3f ^ DAT_7ffa1b398920)) >> 0x3f;
    uVar9 = ((DAT_7ffa1b398920 ^ *param_1) - uVar7 & ~(DAT_7ffa1b398920 ^ uVar5) | uVar5 & uVar7) >>
            0x3f ^ DAT_7ffa1b398920;
    uVar7 = DAT_7ffa1b398920 >> 1;
    uVar4 = 1;
    uVar5 = DAT_7ffa1b398920;
    if (1 < param_4) {
      do {
        puVar1 = param_1 + uVar4;
        uVar4 = uVar4 + 1;
        uVar5 = uVar5 | (longlong)
                        (-((DAT_7ffa1b398920 ^ *puVar1) >> 1) | -(DAT_7ffa1b398920 ^ *puVar1)) >>
                        0x3f;
      } while (uVar4 < param_4);
    }
    uVar4 = FUN_7ffa1b074a70(param_1,param_3,param_4);
    if ((uVar4 & (uVar5 | 0xffffffffffffffffU - ((longlong)(-uVar7 | -uVar9) >> 0x3f))) !=
        DAT_7ffa1b398920) {
      return uVar3 & 0xffffffff;
    }
  }
  return 0xfffffff2;
}



// ==================================================================

// FUN_7ffa1b063180 @ 0x7ffa1b063180
// signature: undefined FUN_7ffa1b063180()
// ==================================================================

/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */

void FUN_7ffa1b063180(longlong param_1,undefined8 param_2,undefined4 param_3)

{
  undefined1 auStack_68 [32];
  undefined8 local_48;
  undefined4 local_40;
  undefined1 local_38 [32];
  ulonglong local_18;
  
  local_18 = DAT_7ffa1b381040 ^ (ulonglong)auStack_68;
  local_48 = param_2;
  local_40 = param_3;
  FUN_7ffa1b062ee0(param_1,*(longlong *)(param_1 + 0x70) + 0x7c0,local_38,0x20);
  return;
}



// ==================================================================

// FUN_7ffa1b045fd0 @ 0x7ffa1b045fd0
// signature: undefined FUN_7ffa1b045fd0()
// ==================================================================

longlong FUN_7ffa1b045fd0(longlong *param_1)

{
  ulonglong uVar1;
  ulonglong uVar2;
  uint uVar3;
  
  uVar1 = (ulonglong)*(ushort *)((longlong)param_1 + 10);
  uVar3 = (uint)*(ushort *)((longlong)param_1 + 10);
  do {
    uVar1 = uVar1 - 1;
    if ((longlong)uVar1 < 0) {
      return 0;
    }
    uVar3 = uVar3 - 1;
  } while (*(longlong *)(*param_1 + uVar1 * 8) == 0);
  uVar2 = 0x8000000000000000;
  uVar1 = 0;
  do {
    if ((uVar2 & *(ulonglong *)(*param_1 + (longlong)(int)uVar3 * 8)) != 0) break;
    uVar2 = uVar2 >> 1;
    uVar1 = uVar1 + 1;
  } while (uVar1 < 0x40);
  return ((longlong)(int)uVar3 + 1) * 0x40 - uVar1;
}



// ==================================================================

// FUN_7ffa1b046600 @ 0x7ffa1b046600
// signature: undefined FUN_7ffa1b046600()
// ==================================================================

int FUN_7ffa1b046600(longlong *param_1,longlong *param_2)

{
  short sVar1;
  ulonglong uVar2;
  ulonglong *puVar3;
  longlong *plVar4;
  ulonglong uVar5;
  bool bVar6;
  
  uVar5 = (ulonglong)*(ushort *)((longlong)param_1 + 10);
  if (uVar5 != 0) {
    plVar4 = (longlong *)(*param_1 + (uVar5 - 1) * 8);
    do {
      if (*plVar4 != 0) break;
      plVar4 = plVar4 + -1;
      uVar5 = uVar5 - 1;
    } while (uVar5 != 0);
  }
  uVar2 = (ulonglong)*(ushort *)((longlong)param_2 + 10);
  if (uVar2 != 0) {
    plVar4 = (longlong *)(*param_2 + (uVar2 - 1) * 8);
    do {
      if (*plVar4 != 0) break;
      plVar4 = plVar4 + -1;
      uVar2 = uVar2 - 1;
    } while (uVar2 != 0);
  }
  if (uVar5 == 0) {
    if (uVar2 == 0) {
      return 0;
    }
  }
  else if (uVar2 < uVar5) goto LAB_7ffa1b0466d4;
  if (uVar5 < uVar2) {
    return -(int)(short)param_2[1];
  }
  if ((short)param_1[1] < 1) {
    sVar1 = (short)param_2[1];
    bVar6 = sVar1 < 0;
  }
  else {
    sVar1 = (short)param_2[1];
    bVar6 = false;
    if (sVar1 < 0) {
      return 1;
    }
  }
  if ((sVar1 != 0 && !bVar6) && ((short)param_1[1] < 0)) {
    return -1;
  }
  if (uVar5 == 0) {
    return 0;
  }
  puVar3 = (ulonglong *)(*param_1 + -8 + uVar5 * 8);
  while (uVar2 = *(ulonglong *)((*param_2 - *param_1) + (longlong)puVar3), *puVar3 <= uVar2) {
    if (*puVar3 < uVar2) {
      return -(int)(short)param_1[1];
    }
    puVar3 = puVar3 + -1;
    uVar5 = uVar5 - 1;
    if (uVar5 == 0) {
      return 0;
    }
  }
LAB_7ffa1b0466d4:
  return (int)(short)param_1[1];
}



// ==================================================================

// FUN_7ffa1b046830 @ 0x7ffa1b046830
// signature: undefined FUN_7ffa1b046830()
// ==================================================================

ulonglong FUN_7ffa1b046830(longlong *param_1,longlong *param_2,longlong *param_3)

{
  ulonglong *puVar1;
  ushort uVar2;
  longlong lVar3;
  ulonglong uVar4;
  ulonglong *puVar5;
  ulonglong uVar6;
  ulonglong uVar7;
  ulonglong uVar8;
  longlong lVar9;
  longlong *plVar10;
  ulonglong uVar11;
  ulonglong *puVar12;
  
  uVar6 = (ulonglong)*(ushort *)((longlong)param_3 + 10);
  if (uVar6 != 0) {
    plVar10 = (longlong *)(*param_3 + (uVar6 - 1) * 8);
    do {
      if (*plVar10 != 0) break;
      plVar10 = plVar10 + -1;
      uVar6 = uVar6 - 1;
    } while (uVar6 != 0);
  }
  if (*(ushort *)((longlong)param_2 + 10) < uVar6) {
    return 0xfffffff6;
  }
  uVar4 = FUN_7ffa1b045900();
  if ((int)uVar4 != 0) {
    return uVar4;
  }
  if ((uVar6 < *(ushort *)((longlong)param_2 + 10)) && (param_2 != param_1)) {
    FUN_7ffa1b2ecc80(*param_1 + uVar6 * 8,*param_2 + uVar6 * 8,
                     (*(ushort *)((longlong)param_2 + 10) - uVar6) * 8);
  }
  uVar2 = *(ushort *)((longlong)param_2 + 10);
  if (uVar2 < *(ushort *)((longlong)param_1 + 10)) {
    FUN_7ffa1b2ec8c0(*param_1 + (ulonglong)uVar2 * 8,0,
                     ((ulonglong)*(ushort *)((longlong)param_1 + 10) - (ulonglong)uVar2) * 8);
  }
  lVar9 = *param_2;
  uVar11 = 0;
  puVar5 = (ulonglong *)*param_3;
  lVar3 = *param_1;
  if (uVar6 != 0) {
    uVar7 = uVar6;
    puVar12 = puVar5;
    do {
      puVar1 = puVar12 + 1;
      uVar8 = *(longlong *)((lVar9 - (longlong)puVar5) + (longlong)puVar12) - uVar11;
      uVar11 = (ulonglong)(uVar8 < *puVar12) +
               (ulonglong)
               (*(ulonglong *)((lVar9 - (longlong)puVar5) + -8 + (longlong)puVar1) < uVar11);
      *(ulonglong *)((lVar3 - (longlong)puVar5) + -8 + (longlong)puVar1) = uVar8 - *puVar12;
      uVar7 = uVar7 - 1;
      puVar12 = puVar1;
    } while (uVar7 != 0);
    if (uVar11 != 0) {
      lVar9 = *(ushort *)((longlong)param_1 + 10) - uVar6;
      puVar5 = (ulonglong *)(*param_1 + uVar6 * 8);
      if (lVar9 != 0) {
        do {
          uVar6 = *puVar5;
          uVar7 = uVar6 - uVar11;
          *puVar5 = uVar7;
          uVar11 = (ulonglong)(uVar6 < uVar7);
          lVar9 = lVar9 + -1;
          puVar5 = puVar5 + 1;
        } while (lVar9 != 0);
        if (uVar7 <= uVar6) goto LAB_7ffa1b04699d;
      }
      return 0xfffffff6;
    }
  }
LAB_7ffa1b04699d:
  *(undefined2 *)(param_1 + 1) = 1;
  return uVar4 & 0xffffffff;
}



// ==================================================================

// FUN_7ffa1b0469c0 @ 0x7ffa1b0469c0
// signature: undefined FUN_7ffa1b0469c0()
// ==================================================================

void FUN_7ffa1b0469c0(longlong param_1,longlong param_2,longlong param_3,int param_4)

{
  int iVar1;
  int iVar2;
  short sVar3;
  
  sVar3 = *(short *)(param_2 + 8);
  if ((int)*(short *)(param_3 + 8) * (int)sVar3 * param_4 < 0) {
    iVar1 = FUN_7ffa1b046560(param_2,param_3);
    if (iVar1 < 0) {
      iVar1 = FUN_7ffa1b046830(param_1,param_3,param_2);
      if (iVar1 != 0) {
        return;
      }
      sVar3 = -sVar3;
    }
    else {
      iVar2 = FUN_7ffa1b046830(param_1,param_2,param_3);
      if (iVar2 != 0) {
        return;
      }
      if (iVar1 == 0) {
        sVar3 = 1;
      }
    }
    *(short *)(param_1 + 8) = sVar3;
  }
  else {
    iVar1 = FUN_7ffa1b0466e0();
    if (iVar1 == 0) {
      *(short *)(param_1 + 8) = sVar3;
    }
  }
  return;
}



// ==================================================================

// FUN_7ffa1b046d10 @ 0x7ffa1b046d10
// signature: undefined FUN_7ffa1b046d10()
// ==================================================================

int FUN_7ffa1b046d10(undefined1 **param_1,undefined1 **param_2,undefined1 **param_3)

{
  int iVar1;
  undefined1 *puVar2;
  longlong lVar3;
  longlong *plVar4;
  undefined1 *puVar5;
  undefined1 *puVar6;
  ulonglong uVar7;
  ulonglong uVar8;
  bool bVar9;
  bool bVar10;
  undefined1 **local_res10;
  undefined1 *local_58;
  undefined4 local_50;
  undefined1 *local_48;
  undefined2 local_40;
  ushort uStack_3e;
  
  local_50 = 1;
  puVar6 = (undefined1 *)0x0;
  local_58 = (undefined1 *)0x0;
  puVar5 = (undefined1 *)0x0;
  local_40 = 1;
  uStack_3e = 0;
  local_48 = (undefined1 *)0x0;
  local_res10 = param_2;
  if (param_1 == param_2) {
    if ((&local_58 != param_2) && (*(ushort *)((longlong)param_2 + 10) != 0)) {
      lVar3 = (ulonglong)*(ushort *)((longlong)param_2 + 10) - 1;
      if (lVar3 != 0) {
        plVar4 = (longlong *)(*param_2 + lVar3 * 8);
        do {
          if (*plVar4 != 0) break;
          plVar4 = plVar4 + -1;
          lVar3 = lVar3 + -1;
        } while (lVar3 != 0);
      }
      uVar7 = lVar3 + 1;
      local_50 = (uint)*(ushort *)(param_2 + 1);
      if (uVar7 == 0) {
        FUN_7ffa1b2ec8c0(0,0,0);
      }
      else {
        if (10000 < uVar7) {
          iVar1 = -0x10;
          goto LAB_7ffa1b047032;
        }
        puVar2 = (undefined1 *)_calloc_base(uVar7,8);
        if (puVar2 == (undefined1 *)0x0) {
          iVar1 = -0x10;
          goto LAB_7ffa1b047032;
        }
        local_50 = CONCAT22((short)uVar7,(undefined2)local_50);
        puVar6 = puVar2;
        local_58 = puVar2;
      }
      FUN_7ffa1b2ecc80(puVar6,*param_2,uVar7 * 8);
    }
    local_res10 = &local_58;
  }
  if (param_1 == param_3) {
    if ((&local_48 != param_3) && (*(ushort *)((longlong)param_3 + 10) != 0)) {
      lVar3 = (ulonglong)*(ushort *)((longlong)param_3 + 10) - 1;
      if (lVar3 != 0) {
        plVar4 = (longlong *)(*param_3 + lVar3 * 8);
        do {
          if (*plVar4 != 0) break;
          plVar4 = plVar4 + -1;
          lVar3 = lVar3 + -1;
        } while (lVar3 != 0);
      }
      local_40 = *(undefined2 *)(param_3 + 1);
      uVar7 = lVar3 + 1;
      if (uVar7 == 0) {
        FUN_7ffa1b2ec8c0(0,0,0);
      }
      else {
        if (10000 < uVar7) {
          iVar1 = -0x10;
          goto LAB_7ffa1b047032;
        }
        puVar2 = (undefined1 *)_calloc_base(uVar7,8);
        if (puVar2 == (undefined1 *)0x0) {
          iVar1 = -0x10;
          goto LAB_7ffa1b047032;
        }
        uStack_3e = (ushort)uVar7;
        puVar5 = puVar2;
        local_48 = puVar2;
      }
      FUN_7ffa1b2ecc80(puVar5,*param_3,uVar7 * 8);
    }
    param_3 = &local_48;
  }
  uVar7 = (ulonglong)*(ushort *)((longlong)local_res10 + 10);
  bVar9 = uVar7 == 0;
  if (!bVar9) {
    plVar4 = (longlong *)(*local_res10 + (uVar7 - 1) * 8);
    do {
      if (*plVar4 != 0) break;
      plVar4 = plVar4 + -1;
      uVar7 = uVar7 - 1;
    } while (uVar7 != 0);
    bVar9 = uVar7 == 0;
  }
  uVar8 = (ulonglong)*(ushort *)((longlong)param_3 + 10);
  bVar10 = uVar8 == 0;
  if (!bVar10) {
    plVar4 = (longlong *)(*param_3 + (uVar8 - 1) * 8);
    do {
      if (*plVar4 != 0) break;
      plVar4 = plVar4 + -1;
      uVar8 = uVar8 - 1;
    } while (uVar8 != 0);
    bVar10 = uVar8 == 0;
  }
  if (bVar10) {
    bVar9 = true;
  }
  iVar1 = FUN_7ffa1b045900(param_1,uVar8 + uVar7);
  if (iVar1 == 0) {
    iVar1 = FUN_7ffa1b045d10(param_1,0);
    if (iVar1 == 0) {
      puVar5 = *param_3;
      puVar6 = *local_res10;
      puVar2 = *param_1;
      FUN_7ffa1b2ec8c0(puVar2,0,(uVar8 + uVar7) * 8);
      if (uVar8 != 0) {
        lVar3 = (longlong)puVar5 - (longlong)puVar2;
        do {
          FUN_7ffa1b074e60(puVar2,uVar7 + 1,puVar6,uVar7,*(undefined8 *)(puVar2 + lVar3));
          puVar2 = puVar2 + 8;
          uVar8 = uVar8 - 1;
        } while (uVar8 != 0);
      }
      puVar5 = local_48;
      puVar6 = local_58;
      if (bVar9) {
        *(undefined2 *)(param_1 + 1) = 1;
      }
      else {
        *(short *)(param_1 + 1) = *(short *)(local_res10 + 1) * *(short *)(param_3 + 1);
      }
      goto LAB_7ffa1b047032;
    }
  }
  puVar6 = local_58;
LAB_7ffa1b047032:
  if (puVar5 != (undefined1 *)0x0) {
    lVar3 = (ulonglong)uStack_3e << 3;
    if ((ulonglong)uStack_3e != 0) {
      puVar2 = puVar5;
      for (; lVar3 != 0; lVar3 = lVar3 + -1) {
        *puVar2 = 0;
        puVar2 = puVar2 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar5);
  }
  if (puVar6 != (undefined1 *)0x0) {
    lVar3 = (ulonglong)local_50._2_2_ << 3;
    if ((ulonglong)local_50._2_2_ != 0) {
      puVar5 = puVar6;
      for (; lVar3 != 0; lVar3 = lVar3 + -1) {
        *puVar5 = 0;
        puVar5 = puVar5 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar6);
  }
  return iVar1;
}



// ==================================================================

// FUN_7ffa1b048740 @ 0x7ffa1b048740
// signature: undefined FUN_7ffa1b048740()
// ==================================================================

int FUN_7ffa1b048740(undefined8 param_1,undefined8 param_2,undefined8 param_3)

{
  int iVar1;
  undefined8 local_res20;
  undefined8 *local_18;
  undefined4 local_10;
  
  local_10 = 0x10001;
  local_res20 = 0;
  local_18 = &local_res20;
  iVar1 = FUN_7ffa1b046600(param_3,&local_18);
  if (iVar1 < 0) {
    iVar1 = -10;
  }
  else {
    iVar1 = FUN_7ffa1b0472f0(0,param_1,param_2,param_3);
    if (iVar1 == 0) {
      local_res20 = 0;
      do {
        local_18 = &local_res20;
        local_10 = 0x10001;
        iVar1 = FUN_7ffa1b046600(param_1,&local_18);
        if (-1 < iVar1) {
          iVar1 = FUN_7ffa1b046600(param_1,param_3);
          while( true ) {
            if (iVar1 < 0) {
              return 0;
            }
            iVar1 = FUN_7ffa1b0469c0(param_1,param_1,param_3,0xffffffff);
            if (iVar1 != 0) break;
            iVar1 = FUN_7ffa1b046600(param_1,param_3);
          }
          return iVar1;
        }
        iVar1 = FUN_7ffa1b0469c0(param_1,param_1,param_3,1);
      } while (iVar1 == 0);
    }
  }
  return iVar1;
}



// ==================================================================

// FUN_7ffa1b0c8950 @ 0x7ffa1b0c8950
// signature: undefined FUN_7ffa1b0c8950()
// ==================================================================

void FUN_7ffa1b0c8950(longlong param_1)

{
  undefined4 *puVar1;
  int iVar2;
  undefined4 uVar3;
  
  if ((param_1 != 0) && (iVar2 = (*DAT_7ffa1b2ef138)(DAT_7ffa1b397958,0,param_1), iVar2 == 0)) {
    uVar3 = (*DAT_7ffa1b2ef088)();
    uVar3 = FUN_7ffa1b0c8768(uVar3);
    puVar1 = (undefined4 *)FUN_7ffa1b0c88a8();
    *puVar1 = uVar3;
  }
  return;
}



// ==================================================================

// FUN_7ffa1b0457a0 @ 0x7ffa1b0457a0
// signature: undefined FUN_7ffa1b0457a0()
// ==================================================================

int FUN_7ffa1b0457a0(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

{
  short sVar1;
  ushort uVar2;
  ushort uVar3;
  int iVar4;
  ulonglong uVar5;
  
  if (param_1 == param_2) {
    return 0;
  }
  uVar5 = DAT_7ffa1b398920 ^ param_3 & 0xff;
  uVar5 = -(uVar5 >> 1) | -uVar5;
  iVar4 = FUN_7ffa1b045900(param_1,*(undefined2 *)((longlong)param_2 + 10));
  if (iVar4 == 0) {
    iVar4 = FUN_7ffa1b045900(param_2,*(undefined2 *)((longlong)param_1 + 10));
    if (iVar4 == 0) {
      uVar2 = (ushort)DAT_7ffa1b398920;
      uVar3 = (ushort)((longlong)uVar5 >> 0x3f);
      sVar1 = *(short *)(param_1 + 1);
      *(ushort *)(param_1 + 1) =
           (*(short *)(param_1 + 1) + 1U & ~(uVar2 ^ uVar3) | *(short *)(param_2 + 1) + 1U & uVar3)
           - 1;
      *(ushort *)(param_2 + 1) =
           (*(short *)(param_2 + 1) + 1U & ~(uVar2 ^ uVar3) | sVar1 + 1U & uVar3) - 1;
      FUN_7ffa1b074bf0(*param_1,*param_2,*(undefined2 *)((longlong)param_1 + 10),
                       (longlong)uVar5 >> 0x3f);
    }
  }
  return iVar4;
}



// ==================================================================

// FUN_7ffa1b045900 @ 0x7ffa1b045900
// signature: undefined FUN_7ffa1b045900()
// ==================================================================

undefined8 FUN_7ffa1b045900(longlong *param_1,ulonglong param_2)

{
  undefined1 *puVar1;
  longlong lVar2;
  longlong lVar3;
  undefined1 *puVar4;
  
  if (10000 < param_2) {
    return 0xfffffff0;
  }
  if (*(ushort *)((longlong)param_1 + 10) < param_2) {
    lVar2 = _calloc_base(param_2,8);
    if (lVar2 == 0) {
      return 0xfffffff0;
    }
    if (*param_1 != 0) {
      FUN_7ffa1b2ecc80(lVar2,*param_1,(ulonglong)*(ushort *)((longlong)param_1 + 10) << 3);
      puVar1 = (undefined1 *)*param_1;
      if ((puVar1 != (undefined1 *)0x0) &&
         (lVar3 = (ulonglong)*(ushort *)((longlong)param_1 + 10) << 3,
         (ulonglong)*(ushort *)((longlong)param_1 + 10) != 0)) {
        puVar4 = puVar1;
        for (; lVar3 != 0; lVar3 = lVar3 + -1) {
          *puVar4 = 0;
          puVar4 = puVar4 + 1;
        }
      }
      thunk_FUN_7ffa1b0c8950(puVar1);
    }
    *(short *)((longlong)param_1 + 10) = (short)param_2;
    *param_1 = lVar2;
  }
  return 0;
}



// ==================================================================

// FUN_7ffa1b045c10 @ 0x7ffa1b045c10
// signature: undefined FUN_7ffa1b045c10()
// ==================================================================

int FUN_7ffa1b045c10(longlong *param_1,longlong *param_2)

{
  int iVar1;
  longlong *plVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  if (param_1 == param_2) {
    return 0;
  }
  if (*(ushort *)((longlong)param_2 + 10) == 0) {
    if (*(ushort *)((longlong)param_1 + 10) == 0) {
      return 0;
    }
    *(undefined2 *)(param_1 + 1) = 1;
    FUN_7ffa1b2ec8c0(*param_1,0,(ulonglong)*(ushort *)((longlong)param_1 + 10) << 3);
    return 0;
  }
  lVar3 = (ulonglong)*(ushort *)((longlong)param_2 + 10) - 1;
  if (lVar3 != 0) {
    plVar2 = (longlong *)(*param_2 + lVar3 * 8);
    do {
      if (*plVar2 != 0) break;
      plVar2 = plVar2 + -1;
      lVar3 = lVar3 + -1;
    } while (lVar3 != 0);
  }
  uVar4 = lVar3 + 1;
  *(short *)(param_1 + 1) = (short)param_2[1];
  if (*(ushort *)((longlong)param_1 + 10) < uVar4) {
    iVar1 = FUN_7ffa1b045900(param_1,uVar4);
    if (iVar1 != 0) {
      return iVar1;
    }
  }
  else {
    FUN_7ffa1b2ec8c0(*param_1 + uVar4 * 8,0,(*(ushort *)((longlong)param_1 + 10) - uVar4) * 8);
  }
  FUN_7ffa1b2ecc80(*param_1,*param_2,uVar4 * 8);
  return 0;
}



// ==================================================================
