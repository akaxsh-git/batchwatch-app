package org.batchwatch.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.batchwatch.app.domain.util.ConfusableChars
import org.batchwatch.app.ui.theme.ConfusableHighlight

@Composable
fun ConfusableBatchText(
    batch: String,
    modifier: Modifier = Modifier
) {
    val analysis = remember(batch) { ConfusableChars.analyze(batch) }
    var selectedHint by remember { mutableStateOf<String?>(null) }

    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .background(Color(0xFFF1F5F9), RoundedCornerShape(8.dp))
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            analysis.forEach { item ->
                if (item.isConfusable) {
                    Box(
                        modifier = Modifier
                            .padding(horizontal = 1.dp)
                            .background(ConfusableHighlight, RoundedCornerShape(4.dp))
                            .border(1.dp, Color(0xFFF59E0B), RoundedCornerShape(4.dp))
                            .clickable { selectedHint = item.hint }
                            .padding(horizontal = 4.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = item.char.toString(),
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            fontSize = 20.sp,
                            color = Color(0xFF92400E)
                        )
                    }
                } else {
                    Text(
                        text = item.char.toString(),
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 20.sp,
                        color = Color(0xFF0F172A),
                        modifier = Modifier.padding(horizontal = 2.dp)
                    )
                }
            }
        }

        if (analysis.any { it.isConfusable }) {
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "Highlighted characters can easily be misread (0/O, 1/I, 5/S, 8/B, 2/Z). Tap to view lookalikes.",
                fontSize = 12.sp,
                color = Color(0xFFD97706),
                style = MaterialTheme.typography.labelSmall
            )
        }
    }

    selectedHint?.let { hint ->
        AlertDialog(
            onDismissRequest = { selectedHint = null },
            title = { Text(text = "Character Confusion Warning") },
            text = { Text(text = hint) },
            confirmButton = {
                TextButton(onClick = { selectedHint = null }) {
                    Text("OK")
                }
            }
        )
    }
}
