package org.batchwatch.app.domain.util

import org.batchwatch.app.domain.model.ExpiryAlertLevel
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale
import java.util.regex.Pattern

object ExpiryCalculator {

    private val MONTH_MAP = mapOf(
        "JAN" to 1, "FEB" to 2, "MAR" to 3, "APR" to 4, "MAY" to 5, "JUN" to 6,
        "JUL" to 7, "AUG" to 8, "SEP" to 9, "OCT" to 10, "NOV" to 11, "DEC" to 12
    )

    fun calculateStatus(expiryText: String?, now: LocalDate = LocalDate.now()): ExpiryAlertLevel {
        val targetDate = parseExpiryDate(expiryText) ?: return ExpiryAlertLevel.UNKNOWN

        return when {
            targetDate.isBefore(now) -> ExpiryAlertLevel.EXPIRED
            ChronoUnit.DAYS.between(now, targetDate) in 0..60 -> ExpiryAlertLevel.EXPIRING_SOON
            else -> ExpiryAlertLevel.VALID
        }
    }

    fun parseExpiryDate(raw: String?): LocalDate? {
        if (raw.isNullOrBlank()) return null
        val clean = raw.trim().uppercase()

        // 1. Match DD/MM/YYYY or DD-MM-YYYY
        val dmyPattern = Pattern.compile("(\\d{1,2})[/-](\\d{1,2})[/-](\\d{4})")
        val dmyMatcher = dmyPattern.matcher(clean)
        if (dmyMatcher.find()) {
            val d = dmyMatcher.group(1)?.toIntOrNull() ?: 1
            val m = dmyMatcher.group(2)?.toIntOrNull() ?: 1
            val y = dmyMatcher.group(3)?.toIntOrNull() ?: 2026
            return try { LocalDate.of(y, m, d) } catch (_: Exception) { null }
        }

        // 2. Match MM/YYYY or MM-YYYY
        val myPattern = Pattern.compile("(\\d{1,2})[/-](\\d{4})")
        val myMatcher = myPattern.matcher(clean)
        if (myMatcher.find()) {
            val m = myMatcher.group(1)?.toIntOrNull() ?: 1
            val y = myMatcher.group(2)?.toIntOrNull() ?: 2026
            return try {
                val ym = YearMonth.of(y, m)
                ym.atEndOfMonth()
            } catch (_: Exception) { null }
        }

        // 3. Match MM/YY or MM-YY
        val myShortPattern = Pattern.compile("(\\d{1,2})[/-](\\d{2})\\b")
        val myShortMatcher = myShortPattern.matcher(clean)
        if (myShortMatcher.find()) {
            val m = myShortMatcher.group(1)?.toIntOrNull() ?: 1
            val yy = myShortMatcher.group(2)?.toIntOrNull() ?: 26
            val y = 2000 + yy
            return try {
                YearMonth.of(y, m).atEndOfMonth()
            } catch (_: Exception) { null }
        }

        // 4. Match MON YYYY or MON-YYYY (e.g. DEC 2026)
        for ((mon, num) in MONTH_MAP) {
            if (clean.contains(mon)) {
                val yearMatcher = Pattern.compile("(\\d{4})").matcher(clean)
                if (yearMatcher.find()) {
                    val y = yearMatcher.group(1)?.toIntOrNull() ?: 2026
                    return try { YearMonth.of(y, num).atEndOfMonth() } catch (_: Exception) { null }
                }
            }
        }

        return null
    }

    fun formatDaysRemaining(expiryText: String?, now: LocalDate = LocalDate.now()): String? {
        val targetDate = parseExpiryDate(expiryText) ?: return null
        val days = ChronoUnit.DAYS.between(now, targetDate)
        return when {
            days < 0 -> "Expired ${-days} day(s) ago"
            days == 0L -> "Expires today"
            days <= 60 -> "Expires in $days days"
            else -> "Valid until ${targetDate.format(DateTimeFormatter.ofPattern("MMM yyyy", Locale.ENGLISH))}"
        }
    }
}
