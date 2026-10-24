package org.batchwatch.app.domain

import org.batchwatch.app.domain.model.ExpiryAlertLevel
import org.batchwatch.app.domain.util.ExpiryCalculator
import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDate

class ExpiryCalculatorTest {

    private val fixedNow = LocalDate.of(2026, 10, 24)

    @Test
    fun testParseMonthYear() {
        val date = ExpiryCalculator.parseExpiryDate("12/2026")
        assertEquals(LocalDate.of(2026, 12, 31), date)
    }

    @Test
    fun testParseDayMonthYear() {
        val date = ExpiryCalculator.parseExpiryDate("15/04/2027")
        assertEquals(LocalDate.of(2027, 4, 15), date)
    }

    @Test
    fun testExpiredMedicine() {
        val status = ExpiryCalculator.calculateStatus("01/2025", now = fixedNow)
        assertEquals(ExpiryAlertLevel.EXPIRED, status)
    }

    @Test
    fun testExpiringSoonMedicine() {
        // Nov 2026 is within 60 days of Oct 24, 2026
        val status = ExpiryCalculator.calculateStatus("11/2026", now = fixedNow)
        assertEquals(ExpiryAlertLevel.EXPIRING_SOON, status)
    }

    @Test
    fun testValidMedicine() {
        // Dec 2027 is far in future
        val status = ExpiryCalculator.calculateStatus("12/2027", now = fixedNow)
        assertEquals(ExpiryAlertLevel.VALID, status)
    }

    @Test
    fun testInvalidDateReturnsUnknown() {
        val status = ExpiryCalculator.calculateStatus("NOT_A_DATE", now = fixedNow)
        assertEquals(ExpiryAlertLevel.UNKNOWN, status)
    }
}
