package org.batchwatch.app.data

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.runBlocking
import org.batchwatch.app.data.local.MedicineDao
import org.batchwatch.app.data.local.MedicineEntity
import org.batchwatch.app.data.local.UserPreferences
import org.batchwatch.app.data.repository.DemoRepository
import org.batchwatch.app.domain.model.CheckVerdict
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class DemoRepositoryTest {

    private lateinit var repository: DemoRepository
    private val fakeDao = FakeMedicineDao()
    private val fakePreferences = FakeUserPreferences()

    @Before
    fun setup() {
        repository = DemoRepository(fakeDao, fakePreferences)
    }

    @Test
    fun testScenario1_Cefixime_IsFlaggedInTwoAlerts() = runBlocking {
        val result = repository.checkBatch("CFX2024", "Cefixime 200mg").getOrThrow()
        assertEquals(CheckVerdict.FLAGGED, result.verdict)
        assertEquals(2, result.matchedAlerts.size)
        assertTrue(result.plainLanguageExplanation.contains("2 separate CDSCO alerts"))
        assertFalse(result.plainLanguageExplanation.contains("safe", ignoreCase = true))
    }

    @Test
    fun testScenario2_Pantoprazole_MisreadIsPossible() = runBlocking {
        // AI reads batch as BCV4OO1DZ
        val result = repository.checkBatch("BCV4OO1DZ", "Pantocid 40").getOrThrow()
        assertEquals(CheckVerdict.POSSIBLE, result.verdict)
        assertTrue(result.plainLanguageExplanation.contains("BCV4001DZ"))
        assertFalse(result.plainLanguageExplanation.contains("safe", ignoreCase = true))
    }

    @Test
    fun testScenario2_Pantoprazole_CorrectedIsFlagged() = runBlocking {
        // Human corrects to BCV4001DZ
        val result = repository.checkBatch("BCV4001DZ", "Pantocid 40").getOrThrow()
        assertEquals(CheckVerdict.FLAGGED, result.verdict)
        assertEquals(1, result.matchedAlerts.size)
        assertFalse(result.plainLanguageExplanation.contains("safe", ignoreCase = true))
    }

    @Test
    fun testScenario3_Telmisartan_Flow() = runBlocking {
        // Initial check: Not found in published alerts
        val initialResult = repository.checkBatch("TEL2026B", "Telmisartan 40").getOrThrow()
        assertEquals(CheckVerdict.NOT_FOUND_IN_ALERTS, initialResult.verdict)
        assertTrue(initialResult.matchedAlerts.isEmpty())

        // Save to fake DAO
        fakeDao.entities.add(
            MedicineEntity(
                id = 1,
                brand = "Telmisartan 40",
                manufacturer = "Apex LifeSciences",
                batch = "TEL2026B",
                expiry = "12/2027",
                verdict = CheckVerdict.NOT_FOUND_IN_ALERTS.name,
                citation = null
            )
        )

        // Trigger simulation
        repository.simulateNewAlertForTelmisartan()

        // Check again: Now FLAGGED in new monthly alert
        val updatedResult = repository.checkBatch("TEL2026B", "Telmisartan 40").getOrThrow()
        assertEquals(CheckVerdict.FLAGGED, updatedResult.verdict)
        assertEquals(1, updatedResult.matchedAlerts.size)
    }

    @Test
    fun testNeverSaySafeRuleAcrossAllScenarios() = runBlocking {
        val testBatches = listOf("CFX2024", "BCV4OO1DZ", "BCV4001DZ", "TEL2026B", "RANDOM123")
        for (batch in testBatches) {
            val result = repository.checkBatch(batch).getOrThrow()
            assertFalse("Explanation must never contain the word 'safe'",
                result.plainLanguageExplanation.contains("\\bsafe\\b".toRegex(RegexOption.IGNORE_CASE)))
        }
    }
}

// Simple in-memory fakes for unit testing
private class FakeMedicineDao : MedicineDao {
    val entities = mutableListOf<MedicineEntity>()

    override fun getAllMedicines(): Flow<List<MedicineEntity>> = flowOf(entities)
    override suspend fun getMedicineById(id: Long): MedicineEntity? = entities.find { it.id == id }
    override suspend fun getMedicineByBatch(batch: String): MedicineEntity? = entities.find { it.batch == batch }
    override suspend fun insertMedicine(entity: MedicineEntity): Long {
        entities.add(entity)
        return entity.id
    }
    override suspend fun updateMedicine(entity: MedicineEntity) {
        val index = entities.indexOfFirst { it.id == entity.id }
        if (index != -1) entities[index] = entity
    }
    override suspend fun deleteMedicine(entity: MedicineEntity) {
        entities.remove(entity)
    }
    override suspend fun deleteById(id: Long) {
        entities.removeIf { it.id == id }
    }
    override fun getCount(): Flow<Int> = flowOf(entities.size)
}

private class FakeUserPreferences : UserPreferences {
    override val isOnboardingCompleted: Flow<Boolean> = flowOf(true)
    override suspend fun setOnboardingCompleted(completed: Boolean) {}

    var simulateEnabled = false
    override val isSimulateNewAlertEnabled: Flow<Boolean> = flowOf(simulateEnabled)
    override suspend fun setSimulateNewAlert(enabled: Boolean) {
        simulateEnabled = enabled
    }

    override val lastAlertVersion: Flow<String?> = flowOf("2026-10")
    override suspend fun setLastAlertVersion(version: String) {}
}
