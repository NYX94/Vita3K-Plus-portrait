package org.vita3k.emulator.ui.screens.emulation

import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.vita3k.emulator.Emulator
import org.vita3k.emulator.NativeLib
import org.vita3k.emulator.NativeCheatSnapshot
import java.io.File
import java.util.Locale

@Composable
internal fun EmulationCheatsTab(
    activity: Emulator,
    titleId: String,
    onStatus: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var snapshot by remember(titleId) { mutableStateOf(NativeLib.getCheatSnapshot()) }
    var status by remember(titleId) { mutableStateOf("") }
    var showEditor by remember { mutableStateOf(false) }
    var editingIndex by remember { mutableStateOf<Int?>(null) }
    var draftName by remember { mutableStateOf("") }
    var draftCodes by remember { mutableStateOf("") }
    var enabledOnBoot by remember { mutableStateOf(false) }

    fun refresh() {
        snapshot = NativeLib.getCheatSnapshot()
    }

    fun openEditor(index: Int?) {
        editingIndex = index
        val entry = index?.let { snapshot.cheats.getOrNull(it) }
        draftName = entry?.name.orEmpty()
        draftCodes = entry?.codes.orEmpty()
        enabledOnBoot = entry?.enabledOnBoot ?: false
        showEditor = true
    }

    LaunchedEffect(titleId) {
        if (titleId.isNotBlank())
            refresh()
    }

    fun importSelectedFile(uri: Uri?) {
        if (uri != null) {
            scope.launch {
                val result = try {
                    val stagedFile = withContext(Dispatchers.IO) {
                        val displayName = context.contentResolver.query(
                            uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null
                        )?.use { cursor ->
                            if (cursor.moveToFirst()) cursor.getString(0) else null
                        } ?: uri.lastPathSegment.orEmpty()
                        val extension = displayName.substringAfterLast('.', "").lowercase(Locale.ROOT)
                        if (extension !in setOf("psv", "db", "txt"))
                            throw IllegalArgumentException("Choose a .psv, .db, or .txt cheat file.")
                        val staged = File.createTempFile("vita-cheats-", ".$extension", context.cacheDir)
                        try {
                            val input = context.contentResolver.openInputStream(uri)
                                ?: throw IllegalStateException("Android could not open that file.")
                            input.use { source -> staged.outputStream().use { target -> source.copyTo(target) } }
                            if (staged.length() > 25L * 1024L * 1024L)
                                throw IllegalArgumentException("That cheat file is larger than 25 MB.")
                            staged
                        } catch (error: Exception) {
                            staged.delete()
                            throw error
                        }
                    }
                    try {
                        // Native cheat state and guest memory are changed on the Compose/main thread.
                        NativeLib.importCheatFile(stagedFile.absolutePath, titleId)
                    } finally {
                        stagedFile.delete()
                    }
                } catch (error: Exception) {
                    "Import failed: ${error.message ?: "could not read the selected file"}"
                }
                status = result
                refresh()
                onStatus(result)
            }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Cheat Manager", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
        Text("Game: $titleId", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = if (snapshot.masterEnabled) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f)
                else MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.45f),
            shape = RoundedCornerShape(14.dp)
        ) {
            Text(
                text = if (snapshot.masterEnabled) "Global cheat switch is ON."
                    else "Global cheat switch is OFF. Enable cheats in the emulator's global Settings to apply codes.",
                modifier = Modifier.padding(12.dp),
                style = MaterialTheme.typography.bodySmall
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilledTonalButton(onClick = { NativeLib.setAllCheatsEnabled(true); refresh() }) { Text("Enable all") }
            OutlinedButton(onClick = { NativeLib.setAllCheatsEnabled(false); refresh() }) { Text("Disable all") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilledTonalButton(onClick = { openEditor(null) }) {
                Icon(Icons.Default.Add, contentDescription = null)
                Text("Add cheat")
            }
            OutlinedButton(onClick = { activity.launchCheatFilePicker { uri -> importSelectedFile(uri) } }) { Text("Import .PSV / .DB / .TXT") }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = {
                val saved = NativeLib.saveCheats()
                status = if (saved) "Cheat states saved for the next launch." else "Could not save cheat states."
                refresh()
                onStatus(status)
            }) { Text("Save for next boot") }
            TextButton(onClick = { refresh(); status = "Cheat list refreshed." }) { Text("Refresh") }
        }

        if (snapshot.cheats.isEmpty()) {
            Text("No cheats are loaded for this game. Check that its title ID has an entry in your .psv or .db file.",
                style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Text("${snapshot.cheats.size} entries · ${snapshot.cheats.count { it.enabled && !it.broken }} enabled · ${snapshot.cheats.count { it.broken }} unsupported",
                style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            snapshot.cheats.forEachIndexed { index, entry ->
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.36f),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(
                            checked = entry.enabled,
                            enabled = !entry.broken,
                            onCheckedChange = { enabled ->
                                NativeLib.setCheatEnabled(index, enabled)
                                refresh()
                            }
                        )
                        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(entry.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                            Text(
                                "${entry.codes.lineSequence().count { it.isNotBlank() }} code lines · ${if (entry.enabledOnBoot) "on at startup" else "off at startup"}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            if (entry.broken)
                                Text("Unsupported or invalid code — cannot be enabled", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.error)
                        }
                        IconButton(onClick = { openEditor(index) }) {
                            Icon(Icons.Default.Edit, contentDescription = "Edit ${entry.name}")
                        }
                    }
                }
            }
        }
        if (status.isNotBlank())
            Text(status, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }

    if (showEditor) {
        AlertDialog(
            onDismissRequest = { showEditor = false },
            title = { Text(if (editingIndex == null) "Add cheat" else "Edit cheat") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(value = draftName, onValueChange = { draftName = it }, label = { Text("Cheat name") }, singleLine = true)
                    OutlinedTextField(
                        value = draftCodes,
                        onValueChange = { draftCodes = it },
                        label = { Text("VitaCheat codes") },
                        placeholder = { Text("\$0200 00000000 00000001") },
                        minLines = 5,
                        maxLines = 10
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = enabledOnBoot, onCheckedChange = { enabledOnBoot = it })
                        Text("Enable automatically next time the game starts")
                    }
                    Text("Enter one code per line in the format \$XXXX AAAAAAAA BBBBBBBB.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val saved = if (editingIndex == null) {
                        NativeLib.addCheat(draftName.trim(), draftCodes, enabledOnBoot)
                    } else {
                        NativeLib.editCheat(editingIndex!!, draftName.trim(), draftCodes, enabledOnBoot)
                    }
                    if (saved) {
                        showEditor = false
                        status = if (editingIndex == null) "Cheat added." else "Cheat updated."
                        refresh()
                        onStatus(status)
                    } else {
                        status = "Could not save the cheat. Check its name and code lines."
                    }
                }) { Text("Save") }
            },
            dismissButton = { TextButton(onClick = { showEditor = false }) { Text("Cancel") } }
        )
    }
}
