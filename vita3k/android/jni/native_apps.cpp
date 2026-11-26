// Vita3K emulator project
// Copyright (C) 2026 Vita3K team
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License along
// with this program; if not, write to the Free Software Foundation, Inc.,
// 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

#include "android_state.h"

#include <cheat/functions.h>
#include <config/config.h>
#include <kernel/state.h>
#include <mem/state.h>

#include <algorithm>
#include <charconv>
#include <cctype>
#include <sstream>
#include <unordered_set>
#include <vector>

#include <app/functions.h>
#include <compat/functions.h>
#include <config/settings.h>
#include <io/state.h>
#include <util/log.h>

namespace android_cheats {

std::string uppercase(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return value;
}

std::string trim(std::string value) {
    const auto first = std::find_if_not(value.begin(), value.end(), [](unsigned char c) { return std::isspace(c); });
    const auto last = std::find_if_not(value.rbegin(), value.rend(), [](unsigned char c) { return std::isspace(c); }).base();
    return first < last ? std::string(first, last) : std::string{};
}

bool parse_hex(std::string token, uint32_t &value) {
    if (!token.empty() && token.front() == '$')
        token.erase(token.begin());
    else if (token.starts_with("0x") || token.starts_with("0X"))
        token.erase(0, 2);
    if (token.empty() || token.size() > 8)
        return false;
    uint32_t parsed = 0;
    const auto result = std::from_chars(token.data(), token.data() + token.size(), parsed, 16);
    if (result.ec != std::errc{} || result.ptr != token.data() + token.size())
        return false;
    value = parsed;
    return true;
}

bool parse_code_text(const std::string &source, std::vector<cheat::CodeLine> &result) {
    std::istringstream input(source);
    std::string raw;
    while (std::getline(input, raw)) {
        std::string line = trim(raw);
        if (line.empty() || line.front() == '#' || line.front() == ';' || line.starts_with("//"))
            continue;
        const size_t comment = line.find('#');
        if (comment != std::string::npos)
            line = trim(line.substr(0, comment));
        std::istringstream tokens(line);
        std::string control, first, second, extra;
        if (!(tokens >> control >> first >> second) || (tokens >> extra))
            return false;
        uint32_t control_value = 0;
        cheat::CodeLine code;
        if (!parse_hex(control, control_value) || control_value > 0xFFFF
            || !parse_hex(first, code.first) || !parse_hex(second, code.second))
            return false;
        code.control = static_cast<uint16_t>(control_value);
        result.push_back(code);
    }
    return !result.empty();
}

void reload_preserving_toggles(EmuEnvState &emuenv, const std::string &title_id) {
    const cheat::CheatFile before = cheat::snapshot(emuenv.cheat);
    cheat::reload(emuenv.cheat, emuenv.cheat_path, title_id, emuenv.mem,
        [&emuenv](uint32_t address, size_t size) { emuenv.kernel.invalidate_jit_cache(address, size); });
    const cheat::CheatFile after = cheat::snapshot(emuenv.cheat);
    for (size_t i = 0; i < after.cheats.size(); ++i) {
        const auto previous = std::find_if(before.cheats.begin(), before.cheats.end(), [&](const cheat::Cheat &item) {
            return item.name == after.cheats[i].name;
        });
        if (previous != before.cheats.end() && previous->enabled != after.cheats[i].enabled) {
            cheat::set_cheat_enabled(emuenv.cheat, i, previous->enabled, emuenv.mem,
                [&emuenv](uint32_t address, size_t size) { emuenv.kernel.invalidate_jit_cache(address, size); });
        }
    }
}

bool ensure_individual_file(EmuEnvState &emuenv, const std::string &title_id, bool &created) {
    created = false;
    const std::string id = uppercase(title_id);
    const fs::path destination = emuenv.cheat_path / (id + ".psv");
    boost::system::error_code error;
    if (fs::is_regular_file(destination, error))
        return true;

    const fs::path existing = cheat::find_cheat_file(emuenv.cheat_path, id);
    if (existing.empty())
        return true;

    const cheat::CheatFile source = cheat::parse_cheat_file(existing, id);
    if (source.cheats.empty())
        return true;
    if (!cheat::append_cheats(destination, id, source.cheats))
        return false;
    created = true;
    return true;
}

jstring make_string(JNIEnv *env, const std::string &value) {
    return env->NewStringUTF(value.c_str());
}

} // namespace android_cheats

extern "C" {

JNIEXPORT jobjectArray JNICALL
Java_org_vita3k_emulator_NativeLib_getAppListDetailed(JNIEnv *env, jclass) {
    jclass app_info_class = env->FindClass("org/vita3k/emulator/data/NativeAppInfo");
    if (!app_info_class)
        return nullptr;

    jmethodID ctor = env->GetMethodID(app_info_class, "<init>", "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ZIJJ)V");
    if (!ctor)
        return env->NewObjectArray(0, app_info_class, nullptr);

    auto *emuenv = get_emuenv();
    if (!emuenv)
        return env->NewObjectArray(0, app_info_class, nullptr);

    const auto apps = app::get_apps(*emuenv);
    const auto app_times = app::get_user_app_times(*emuenv);
    jobjectArray result = env->NewObjectArray(static_cast<jsize>(apps.size()), app_info_class, nullptr);

    for (jsize i = 0; i < static_cast<jsize>(apps.size()); ++i) {
        const auto &app = apps[static_cast<size_t>(i)];
        const int compat_state = static_cast<int>(compat::get_app_compat(emuenv->compat, app.title_id));
        const bool has_custom_config = config::has_custom_config(emuenv->config_path, app.path);

        int64_t last_played = 0;
        int64_t playtime = 0;
        const auto time_it = app_times.find(app.path);
        if (time_it != app_times.end()) {
            last_played = static_cast<int64_t>(time_it->second.last_time_used);
            playtime = time_it->second.time_used;
        }

        const fs::path icon_path = app.icon_path;
        const std::string icon_full = app.icon_path.empty()
            ? std::string()
            : (icon_path.is_absolute() ? icon_path.generic_string() : (emuenv->vita_fs_path / icon_path).generic_string());

        jstring title_id = env->NewStringUTF(app.title_id.c_str());
        jstring title = env->NewStringUTF(app.title.c_str());
        jstring category = env->NewStringUTF(app.category.c_str());
        jstring app_ver = env->NewStringUTF(app.app_ver.c_str());
        jstring icon_path_str = env->NewStringUTF(icon_full.c_str());

        jobject app_info = env->NewObject(app_info_class, ctor,
            title_id,
            title,
            category,
            app_ver,
            icon_path_str,
            static_cast<jboolean>(has_custom_config),
            static_cast<jint>(compat_state),
            static_cast<jlong>(last_played),
            static_cast<jlong>(playtime));

        env->SetObjectArrayElement(result, i, app_info);
        env->DeleteLocalRef(app_info);
        env->DeleteLocalRef(title_id);
        env->DeleteLocalRef(title);
        env->DeleteLocalRef(category);
        env->DeleteLocalRef(app_ver);
        env->DeleteLocalRef(icon_path_str);
    }

    return result;
}

JNIEXPORT jboolean JNICALL
Java_org_vita3k_emulator_NativeLib_performAppAction(JNIEnv *env, jclass, jstring title_id_str, jint action_bit) {
    auto *emuenv = get_emuenv();
    auto *controller = get_app_session_controller();
    if (!emuenv)
        return JNI_FALSE;

    const std::string title_id = jstring_to_string(env, title_id_str);

    switch (static_cast<uint32_t>(action_bit)) {
    case ACTION_DELETE_APPLICATION: {
        if (controller && controller->has_active_session())
            return JNI_FALSE;
        const auto app = find_app_by_title_id(title_id);
        if (!app.has_value())
            return JNI_FALSE;
        app::delete_app(*emuenv, app->path);
        return JNI_TRUE;
    }
    case ACTION_DELETE_SAVE_DATA: {
        const auto app = find_app_by_title_id(title_id);
        if (!app.has_value())
            return JNI_FALSE;
        return remove_path_if_exists(emuenv->vita_fs_path / "ux0/user" / emuenv->io.user_id / "savedata" / app->savedata)
            ? JNI_TRUE
            : JNI_FALSE;
    }
    case ACTION_DELETE_PATCH: {
        bool removed = false;
        removed |= remove_path_if_exists(emuenv->vita_fs_path / "ux0/patch" / title_id);
        removed |= remove_path_if_exists(emuenv->shared_path / "patch" / title_id);
        return removed ? JNI_TRUE : JNI_FALSE;
    }
    case ACTION_DELETE_DLC: {
        const auto app = find_app_by_title_id(title_id);
        if (!app.has_value())
            return JNI_FALSE;
        return remove_path_if_exists(emuenv->vita_fs_path / "ux0/addcont" / app->addcont)
            ? JNI_TRUE
            : JNI_FALSE;
    }
    case ACTION_DELETE_LICENSE:
        return remove_path_if_exists(emuenv->vita_fs_path / "ux0/license" / title_id)
            ? JNI_TRUE
            : JNI_FALSE;
    case ACTION_DELETE_SHADER_CACHE:
        return remove_path_if_exists(emuenv->cache_path / "shaders" / title_id)
            ? JNI_TRUE
            : JNI_FALSE;
    case ACTION_DELETE_SHADER_LOG: {
        bool removed = false;
        removed |= remove_path_if_exists(emuenv->cache_path / "shaderlog" / title_id);
        removed |= remove_path_if_exists(emuenv->log_path / "shaderlog" / title_id);
        return removed ? JNI_TRUE : JNI_FALSE;
    }
    case ACTION_DELETE_EXPORT_TEXTURES:
        return remove_path_if_exists(emuenv->shared_path / "textures/export" / title_id)
            ? JNI_TRUE
            : JNI_FALSE;
    case ACTION_DELETE_IMPORT_TEXTURES:
        return remove_path_if_exists(emuenv->shared_path / "textures/import" / title_id)
            ? JNI_TRUE
            : JNI_FALSE;
    case ACTION_RESET_LAST_PLAYED: {
        const auto app = find_app_by_title_id(title_id);
        if (!app.has_value())
            return JNI_FALSE;
        app::reset_last_time_app_used(*emuenv, app->path);
        return JNI_TRUE;
    }
    default:
        return JNI_FALSE;
    }
}

JNIEXPORT jint JNICALL
Java_org_vita3k_emulator_NativeLib_getAppActionAvailabilityMask(JNIEnv *env, jclass, jstring title_id_str) {
    auto *emuenv = get_emuenv();
    if (!emuenv)
        return static_cast<jint>(0);

    const std::string title_id = jstring_to_string(env, title_id_str);
    return static_cast<jint>(get_app_action_availability_mask(title_id));
}

JNIEXPORT jlong JNICALL
Java_org_vita3k_emulator_NativeLib_getAppInstallSize(JNIEnv *env, jclass, jstring title_id_str) {
    auto *emuenv = get_emuenv();
    if (!emuenv)
        return 0L;

    const std::string title_id = jstring_to_string(env, title_id_str);
    const auto app = find_app_by_title_id(title_id);
    if (!app.has_value())
        return 0L;

    const auto app_path = emuenv->vita_fs_path / "ux0/app" / app->path;
    if (!fs::exists(app_path))
        return 0L;

    try {
        uintmax_t size = 0;
        for (const auto &entry : fs::recursive_directory_iterator(app_path, fs::directory_options::skip_permission_denied)) {
            if (entry.is_regular_file())
                size += fs::file_size(entry.path());
        }
        return static_cast<jlong>(size);
    } catch (const std::exception &error) {
        LOG_WARN("Failed to compute install size for {}: {}", title_id, error.what());
        return 0L;
    }
}

JNIEXPORT jobjectArray JNICALL
Java_org_vita3k_emulator_NativeLib_getCheatSnapshotRaw(JNIEnv *env, jclass) {
    std::vector<std::string> fields;
    auto *emuenv = get_emuenv();
    if (!emuenv) {
        fields = { "", "0", "0" };
    } else {
        const cheat::CheatFile file = cheat::snapshot(emuenv->cheat);
        fields = { cheat::loaded_title_id(emuenv->cheat), emuenv->cfg.enable_cheats ? "1" : "0", std::to_string(file.cheats.size()) };
        for (const auto &entry : file.cheats) {
            std::string codes;
            for (size_t code_index = 0; code_index < entry.lines.size(); ++code_index) {
                const auto &line = entry.lines[code_index];
                // The final F000 line is an internal marker used only to retain a broken state
                // when a database section is copied into a per-game override.
                if (entry.broken && (code_index + 1 == entry.lines.size()) && (line.control == 0xF000))
                    continue;
                if (!codes.empty())
                    codes.push_back('\n');
                codes += cheat::format_code_line(line);
            }
            fields.push_back(entry.name);
            fields.push_back(entry.enabled ? "1" : "0");
            fields.push_back(entry.broken ? "1" : "0");
            fields.push_back(entry.enabled_on_boot ? "1" : "0");
            fields.push_back(std::move(codes));
        }
    }

    jclass string_class = env->FindClass("java/lang/String");
    if (!string_class)
        return nullptr;
    jobjectArray result = env->NewObjectArray(static_cast<jsize>(fields.size()), string_class, nullptr);
    if (!result)
        return nullptr;
    for (jsize i = 0; i < static_cast<jsize>(fields.size()); ++i) {
        jstring value = env->NewStringUTF(fields[static_cast<size_t>(i)].c_str());
        env->SetObjectArrayElement(result, i, value);
        env->DeleteLocalRef(value);
    }
    return result;
}

JNIEXPORT jboolean JNICALL
Java_org_vita3k_emulator_NativeLib_setCheatEnabled(JNIEnv *, jclass, jint index, jboolean enabled) {
    auto *emuenv = get_emuenv();
    if (!emuenv || index < 0)
        return JNI_FALSE;
    const auto file = cheat::snapshot(emuenv->cheat);
    if (static_cast<size_t>(index) >= file.cheats.size())
        return JNI_FALSE;
    cheat::set_cheat_enabled(emuenv->cheat, static_cast<size_t>(index), enabled == JNI_TRUE, emuenv->mem,
        [emuenv](uint32_t address, size_t size) { emuenv->kernel.invalidate_jit_cache(address, size); });
    return JNI_TRUE;
}

JNIEXPORT jboolean JNICALL
Java_org_vita3k_emulator_NativeLib_setAllCheatsEnabled(JNIEnv *, jclass, jboolean enabled) {
    auto *emuenv = get_emuenv();
    if (!emuenv || cheat::loaded_title_id(emuenv->cheat).empty())
        return JNI_FALSE;
    const auto file = cheat::snapshot(emuenv->cheat);
    for (size_t i = 0; i < file.cheats.size(); ++i) {
        if (!file.cheats[i].broken) {
            cheat::set_cheat_enabled(emuenv->cheat, i, enabled == JNI_TRUE, emuenv->mem,
                [emuenv](uint32_t address, size_t size) { emuenv->kernel.invalidate_jit_cache(address, size); });
        }
    }
    return JNI_TRUE;
}

JNIEXPORT jboolean JNICALL
Java_org_vita3k_emulator_NativeLib_saveCheats(JNIEnv *, jclass) {
    auto *emuenv = get_emuenv();
    if (!emuenv)
        return JNI_FALSE;
    const std::string title_id = cheat::loaded_title_id(emuenv->cheat);
    if (title_id.empty())
        return JNI_FALSE;
    bool created = false;
    if (!android_cheats::ensure_individual_file(*emuenv, title_id, created))
        return JNI_FALSE;
    if (created)
        android_cheats::reload_preserving_toggles(*emuenv, title_id);
    return cheat::save(emuenv->cheat) ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jboolean JNICALL
Java_org_vita3k_emulator_NativeLib_addCheat(JNIEnv *env, jclass, jstring name_value, jstring codes_value, jboolean enabled_on_boot) {
    auto *emuenv = get_emuenv();
    if (!emuenv)
        return JNI_FALSE;
    const std::string title_id = cheat::loaded_title_id(emuenv->cheat);
    const std::string name = android_cheats::trim(jstring_to_string(env, name_value));
    if (title_id.empty() || name.empty())
        return JNI_FALSE;

    cheat::Cheat entry;
    entry.name = name;
    entry.enabled_on_boot = enabled_on_boot == JNI_TRUE;
    entry.enabled = entry.enabled_on_boot;
    if (!android_cheats::parse_code_text(jstring_to_string(env, codes_value), entry.lines))
        return JNI_FALSE;

    bool created = false;
    if (!android_cheats::ensure_individual_file(*emuenv, title_id, created))
        return JNI_FALSE;
    if (created)
        android_cheats::reload_preserving_toggles(*emuenv, title_id);
    return cheat::add_cheat(emuenv->cheat, emuenv->cheat_path, title_id, entry, emuenv->mem,
        [emuenv](uint32_t address, size_t size) { emuenv->kernel.invalidate_jit_cache(address, size); }) ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jboolean JNICALL
Java_org_vita3k_emulator_NativeLib_editCheat(JNIEnv *env, jclass, jint index, jstring name_value, jstring codes_value, jboolean enabled_on_boot) {
    auto *emuenv = get_emuenv();
    if (!emuenv || index < 0)
        return JNI_FALSE;
    const std::string title_id = cheat::loaded_title_id(emuenv->cheat);
    if (title_id.empty())
        return JNI_FALSE;

    bool created = false;
    if (!android_cheats::ensure_individual_file(*emuenv, title_id, created))
        return JNI_FALSE;
    if (created)
        android_cheats::reload_preserving_toggles(*emuenv, title_id);

    const cheat::CheatFile before = cheat::snapshot(emuenv->cheat);
    if (static_cast<size_t>(index) >= before.cheats.size())
        return JNI_FALSE;
    cheat::Cheat replacement = before.cheats[static_cast<size_t>(index)];
    replacement.name = android_cheats::trim(jstring_to_string(env, name_value));
    replacement.enabled_on_boot = enabled_on_boot == JNI_TRUE;
    if (replacement.name.empty())
        return JNI_FALSE;
    replacement.lines.clear();
    if (!android_cheats::parse_code_text(jstring_to_string(env, codes_value), replacement.lines))
        return JNI_FALSE;
    const bool runtime_enabled = before.cheats[static_cast<size_t>(index)].enabled;
    if (!cheat::replace_cheat(before, static_cast<size_t>(index), replacement))
        return JNI_FALSE;

    android_cheats::reload_preserving_toggles(*emuenv, title_id);
    cheat::set_cheat_enabled(emuenv->cheat, static_cast<size_t>(index), runtime_enabled, emuenv->mem,
        [emuenv](uint32_t address, size_t size) { emuenv->kernel.invalidate_jit_cache(address, size); });
    return JNI_TRUE;
}

JNIEXPORT jstring JNICALL
Java_org_vita3k_emulator_NativeLib_importCheatFile(JNIEnv *env, jclass, jstring path_value, jstring title_value) {
    auto *emuenv = get_emuenv();
    if (!emuenv)
        return android_cheats::make_string(env, "Vita3K is not initialized.");
    const std::string title_id = cheat::loaded_title_id(emuenv->cheat);
    const std::string requested_title = android_cheats::uppercase(jstring_to_string(env, title_value));
    if (title_id.empty() || requested_title != android_cheats::uppercase(title_id))
        return android_cheats::make_string(env, "The running game changed. Reopen the Cheats tab and try again.");

    const fs::path source_path(jstring_to_string(env, path_value));
    const std::string extension = android_cheats::uppercase(source_path.extension().string());
    if (extension != ".PSV" && extension != ".DB" && extension != ".TXT")
        return android_cheats::make_string(env, "Choose a .psv, .db, or .txt cheat file.");
    boost::system::error_code size_error;
    if (!fs::is_regular_file(source_path, size_error) || fs::file_size(source_path, size_error) > 25u * 1024u * 1024u)
        return android_cheats::make_string(env, "The selected file is missing or larger than 25 MB.");

    const cheat::CheatFile imported = cheat::parse_cheat_file(source_path, title_id);
    if (imported.cheats.empty())
        return android_cheats::make_string(env, "No cheats for this game's title ID were found in that file.");

    const std::string id = android_cheats::uppercase(title_id);
    const fs::path destination = emuenv->cheat_path / (id + ".psv");
    boost::system::error_code exists_error;
    const bool has_individual = fs::is_regular_file(destination, exists_error);
    cheat::CheatFile existing;
    if (has_individual) {
        existing = cheat::parse_cheat_file(destination, title_id);
    } else {
        const fs::path previous_path = cheat::find_cheat_file(emuenv->cheat_path, title_id);
        if (!previous_path.empty())
            existing = cheat::parse_cheat_file(previous_path, title_id);
    }

    std::unordered_set<std::string> known_names;
    std::vector<cheat::Cheat> to_write;
    if (!has_individual)
        to_write = existing.cheats;
    for (const auto &entry : existing.cheats)
        known_names.insert(android_cheats::uppercase(entry.name));
    size_t skipped_broken = 0;
    for (const auto &entry : imported.cheats) {
        if (entry.broken) {
            ++skipped_broken;
            continue;
        }
        if (known_names.insert(android_cheats::uppercase(entry.name)).second)
            to_write.push_back(entry);
    }

    const size_t added_count = to_write.size() - (has_individual ? 0 : existing.cheats.size());
    if (added_count == 0) {
        return android_cheats::make_string(env, skipped_broken
            ? "No usable new cheats were imported. " + std::to_string(skipped_broken) + " invalid entries were skipped."
            : "No new cheats to import. Existing entries were left unchanged.");
    }
    if (!cheat::append_cheats(destination, title_id, to_write))
        return android_cheats::make_string(env, "Import failed while writing the per-game cheat file.");

    android_cheats::reload_preserving_toggles(*emuenv, title_id);
    return android_cheats::make_string(env, "Imported " + std::to_string(added_count)
        + " new cheats for " + id + ". Skipped " + std::to_string(skipped_broken)
        + " invalid entries. The original combined database was kept unchanged.");
}

} // extern "C"
