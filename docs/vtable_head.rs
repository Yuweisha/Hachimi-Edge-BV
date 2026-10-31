pub struct Vtable {
    pub hachimi_instance: unsafe extern "C" fn() -> *const c_void,
    pub hachimi_get_interceptor: unsafe extern "C" fn(this: *const c_void) -> *const c_void,

    pub interceptor_hook: unsafe extern "C" fn(
        this: *const c_void, orig_addr: *mut c_void, hook_addr: *mut c_void
    ) -> *mut c_void,
    pub interceptor_hook_vtable: unsafe extern "C" fn(
        this: *const c_void, vtable: *mut *mut c_void, vtable_index: usize, hook_addr: *mut c_void
    ) -> *mut c_void,
    pub interceptor_get_trampoline_addr: unsafe extern "C" fn(
        this: *const c_void, hook_addr: *mut c_void
    ) -> *mut c_void,
    pub interceptor_unhook: unsafe extern "C" fn(this: *const c_void, hook_addr: *mut c_void) -> *mut c_void,

    pub il2cpp_resolve_symbol: unsafe extern "C" fn(name: *const c_char) -> *mut c_void,
    pub il2cpp_get_assembly_image: unsafe extern "C" fn(assembly_name: *const c_char) -> *const c_void,
    pub il2cpp_get_class: unsafe extern "C" fn(
        image: *const c_void, namespace: *const c_char, class_name: *const c_char
    ) -> *mut c_void,
    pub il2cpp_get_method: unsafe extern "C" fn(
        class: *mut c_void, name: *const c_char, args_count: i32
    ) -> *const c_void,
    pub il2cpp_get_method_overload: unsafe extern "C" fn(
        class: *mut c_void, name: *const c_char, params: *const Il2CppTypeEnum, param_count: usize
    ) -> *const c_void,
    pub il2cpp_get_method_addr: unsafe extern "C" fn(
        class: *mut c_void, name: *const c_char, args_count: i32
    ) -> *mut c_void,
    pub il2cpp_get_method_overload_addr: unsafe extern "C" fn(
        class: *mut c_void, name: *const c_char, params: *const Il2CppTypeEnum, param_count: usize
    ) -> *mut c_void,
        pub il2cpp_get_method_cached: unsafe extern "C" fn(
        class: *mut c_void, name: *const c_char, args_count: i32
    ) -> *const c_void,
    pub il2cpp_get_method_addr_cached: unsafe extern "C" fn(
        class: *mut c_void, name: *const c_char, args_count: i32
    ) -> *mut c_void,
    pub il2cpp_find_nested_class: unsafe extern "C" fn(
        class: *mut c_void, name: *const c_char
    ) -> *mut c_void,
    pub il2cpp_resolve_icall: unsafe extern "C" fn(name: *const c_char) -> *mut c_void,
    pub il2cpp_class_get_methods: unsafe extern "C" fn(klass: *mut c_void, iter: *mut *mut c_void) -> *const c_void,
    pub il2cpp_get_field_from_name: unsafe extern "C" fn(
        class: *mut c_void, name: *const c_char
    ) -> *mut FieldInfo,
    pub il2cpp_get_field_value: unsafe extern "C" fn(
        obj: *mut c_void, field: *mut FieldInfo, out_value: *mut c_void
    ),
    pub il2cpp_set_field_value: unsafe extern "C" fn(
        obj: *mut c_void, field: *mut FieldInfo, value: *const c_void
    ),
    pub il2cpp_get_static_field_value: unsafe extern "C" fn(
        field: *mut FieldInfo, out_value: *mut c_void
    ),
    pub il2cpp_set_static_field_value: unsafe extern "C" fn(
        field: *mut FieldInfo, value: *const c_void
    ),
    pub il2cpp_object_new: unsafe extern "C" fn(klass: *const Il2CppClass) -> *mut c_void,
    pub il2cpp_unbox: unsafe extern "C" fn(obj: *mut c_void) -> *mut c_void,
    pub il2cpp_get_main_thread: unsafe extern "C" fn() -> *mut c_void,
    pub il2cpp_get_attached_threads: unsafe extern "C" fn(out_size: *mut usize) -> *mut *mut c_void,
    pub il2cpp_schedule_on_thread: unsafe extern "C" fn(thread: *mut c_void, callback: unsafe extern "C" fn()),
    pub il2cpp_create_array: unsafe extern "C" fn(
        element_type: *mut c_void, length: il2cpp_array_size_t
    ) -> *mut Il2CppArray,
    pub il2cpp_get_singleton_like_instance: unsafe extern "C" fn(class: *mut c_void) -> *mut c_void,

    pub log: unsafe extern "C" fn(level: i32, target: *const c_char, message: *const c_char),
}
