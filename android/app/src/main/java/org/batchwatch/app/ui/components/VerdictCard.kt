package org.batchwatch.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dangerous
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.Divider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.batchwatch.app.domain.model.CheckResult
import org.batchwatch.app.domain.model.CheckVerdict
import org.batchwatch.app.ui.theme.VerdictFlaggedBg
import org.batchwatch.app.ui.theme.VerdictFlaggedBorder
import org.batchwatch.app.ui.theme.VerdictFlaggedText
import org.batchwatch.app.ui.theme.VerdictNotFoundBg
import org.batchwatch.app.ui.theme.VerdictNotFoundBorder
import org.batchwatch.app.ui.theme.VerdictNotFoundText
import org.batchwatch.app.ui.theme.VerdictPossibleBg
import org.batchwatch.app.ui.theme.VerdictPossibleBorder
import org.batchwatch.app.ui.theme.VerdictPossibleText

@Composable
fun VerdictCard(
    result: CheckResult,
    modifier: Modifier = Modifier
) {
    val (bgColor, borderColor, textColor, icon, verdictTitle) = when (result.verdict) {
        CheckVerdict.FLAGGED -> Quintuple(
            VerdictFlaggedBg,
            VerdictFlaggedBorder,
            VerdictFlaggedText,
            Icons.Default.Dangerous,
            "FOUND IN PUBLISHED ALERTS"
        )
        CheckVerdict.POSSIBLE -> Quintuple(
            VerdictPossibleBg,
            VerdictPossibleBorder,
            VerdictPossibleText,
            Icons.Default.HelpOutline,
            "POSSIBLE MATCH · VERIFY PACK"
        )
        CheckVerdict.NOT_FOUND_IN_ALERTS -> Quintuple(
            VerdictNotFoundBg,
            VerdictNotFoundBorder,
            VerdictNotFoundText,
            Icons.Default.Shield,
            "NOT FOUND IN PUBLISHED ALERTS"
        )
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(bgColor)
            .border(1.5.dp, borderColor, RoundedCornerShape(14.dp))
            .padding(18.dp)
    ) {
        // 1. Header Badge + Verdict Title
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = icon,
                contentDescription = result.verdict.label,
                tint = borderColor
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = verdictTitle,
                color = textColor,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp,
                letterSpacing = 0.5.sp
            )
        }

        Spacer(modifier = Modifier.height(10.dp))

        // 2. Query Batch Pill
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = "Batch: ",
                style = MaterialTheme.typography.bodyMedium,
                color = textColor.copy(alpha = 0.8f)
            )
            Box(
                modifier = Modifier
                    .background(Color.White.copy(alpha = 0.7f), RoundedCornerShape(4.dp))
                    .padding(horizontal = 6.dp, vertical = 2.dp)
            ) {
                Text(
                    text = result.queryBatch,
                    fontWeight = FontWeight.SemiBold,
                    fontFamily = FontFamily.Monospace,
                    color = Color.Black
                )
            }
            if (!result.queryProduct.isNullOrBlank()) {
                Text(
                    text = " · ${result.queryProduct}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = textColor.copy(alpha = 0.9f)
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // 3. Plain Language Explanation Box
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White.copy(alpha = 0.85f), RoundedCornerShape(8.dp))
                .padding(12.dp)
        ) {
            Text(
                text = result.plainLanguageExplanation,
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF1E293B),
                lineHeight = 20.sp
            )
        }

        // 4. Source Citation (if available)
        if (!result.citation.isNullOrBlank()) {
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = "Source: ${result.citation}",
                fontSize = 12.sp,
                fontFamily = FontFamily.Monospace,
                color = textColor.copy(alpha = 0.85f)
            )
        }

        // 5. Next Steps
        if (result.nextSteps.isNotEmpty()) {
            Spacer(modifier = Modifier.height(14.dp))
            Divider(color = borderColor.copy(alpha = 0.25f))
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = "Recommended Next Steps:",
                fontWeight = FontWeight.SemiBold,
                fontSize = 13.sp,
                color = textColor
            )
            Spacer(modifier = Modifier.height(6.dp))
            result.nextSteps.forEach { step ->
                Row(
                    modifier = Modifier.padding(vertical = 2.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Text(text = "• ", fontWeight = FontWeight.Bold, color = textColor)
                    Text(
                        text = step,
                        fontSize = 13.sp,
                        color = Color(0xFF334155),
                        lineHeight = 18.sp
                    )
                }
            }
        }

        // 6. Disclaimer
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = result.disclaimer,
            fontSize = 11.sp,
            color = Color(0xFF64748B),
            lineHeight = 15.sp
        )
    }
}

private data class Quintuple<A, B, C, D, E>(
    val first: A,
    val second: B,
    val third: C,
    val fourth: D,
    val fifth: E
)
