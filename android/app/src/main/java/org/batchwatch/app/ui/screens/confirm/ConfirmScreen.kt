package org.batchwatch.app.ui.screens.confirm

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Image
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import org.batchwatch.app.domain.model.ScanDraft
import org.batchwatch.app.ui.components.ConfusableBatchText
import org.batchwatch.app.ui.theme.PrimaryBlue

@Composable
fun ConfirmScreen(
    draft: ScanDraft,
    onConfirm: (batch: String, product: String?, manufacturer: String?) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    var batchInput by remember { mutableStateOf(draft.batch) }
    var productInput by remember { mutableStateOf(draft.brand ?: "") }
    var manufacturerInput by remember { mutableStateOf(draft.manufacturer ?: "") }

    var scale by remember { mutableFloatStateOf(1f) }
    val transformState = rememberTransformableState { zoomChange, _, _ ->
        scale = (scale * zoomChange).coerceIn(1f, 4f)
    }

    val batchConfidence = draft.confidence["batch_number"] ?: 0.65f
    val confidencePct = (batchConfidence * 100).toInt()

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())
            .padding(20.dp)
    ) {
        // Top Bar
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back")
            }
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Confirm Batch Details",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 1. Zoomable Photo Preview
        if (!draft.photoUri.isNullOrBlank()) {
            Text(
                text = "Captured Strip (Pinch to zoom)",
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                color = Color(0xFF64748B)
            )
            Spacer(modifier = Modifier.height(6.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color(0xFFE2E8F0))
            ) {
                AsyncImage(
                    model = draft.photoUri,
                    contentDescription = "Medicine Photo",
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .fillMaxSize()
                        .graphicsLayer(scaleX = scale, scaleY = scale)
                        .transformable(state = transformState)
                )
            }
            Spacer(modifier = Modifier.height(16.dp))
        }

        // 2. Optical Confidence Meter
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFFF1F5F9), RoundedCornerShape(10.dp))
                .padding(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "AI Confidence for Batch Number:",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF334155),
                    modifier = Modifier.weight(1f)
                )
                Text(
                    text = "$confidencePct%",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (confidencePct >= 80) Color(0xFF15803D) else Color(0xFFD97706)
                )
            }
            Spacer(modifier = Modifier.height(6.dp))
            LinearProgressIndicator(
                progress = { batchConfidence },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(4.dp)),
                color = if (confidencePct >= 80) Color(0xFF15803D) else Color(0xFFD97706),
                trackColor = Color(0xFFE2E8F0)
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 3. Confusable Character Highlights
        if (batchInput.isNotBlank()) {
            Text(
                text = "Character Confusion Analysis:",
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(modifier = Modifier.height(6.dp))
            ConfusableBatchText(batch = batchInput)
            Spacer(modifier = Modifier.height(16.dp))
        }

        // 4. Large Editable Batch Input
        OutlinedTextField(
            value = batchInput,
            onValueChange = { batchInput = it },
            label = { Text("Batch Number * (Compare with physical pack)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            textStyle = MaterialTheme.typography.titleLarge.copy(
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold
            )
        )

        Spacer(modifier = Modifier.height(12.dp))

        // 5. Medicine Name & Manufacturer (Optional)
        OutlinedTextField(
            value = productInput,
            onValueChange = { productInput = it },
            label = { Text("Medicine Name (Optional)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        )

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedTextField(
            value = manufacturerInput,
            onValueChange = { manufacturerInput = it },
            label = { Text("Manufacturer (Optional)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        )

        Spacer(modifier = Modifier.height(28.dp))

        // 6. Confirm Button
        Button(
            onClick = {
                if (batchInput.isNotBlank()) {
                    onConfirm(
                        batchInput.trim(),
                        productInput.ifBlank { null },
                        manufacturerInput.ifBlank { null }
                    )
                }
            },
            enabled = batchInput.isNotBlank(),
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Check, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Confirm & Check Alerts",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
        Spacer(modifier = Modifier.height(24.dp))
    }
}
