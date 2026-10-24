package org.batchwatch.app.data.repository

import kotlinx.coroutines.flow.Flow
import org.batchwatch.app.domain.model.CheckResult
import org.batchwatch.app.domain.model.Medicine
import org.batchwatch.app.domain.model.ScanDraft

interface MedicineRepository {

    val isDemoMode: Boolean

    suspend fun scanImage(imageBytes: ByteArray, photoUri: String? = null): Result<ScanDraft>

    suspend fun checkBatch(batch: String, product: String? = null, manufacturer: String? = null): Result<CheckResult>

    suspend fun recheckAll(): Result<List<Pair<Medicine, CheckResult>>>

    fun getSavedMedicines(): Flow<List<Medicine>>

    suspend fun saveMedicine(medicine: Medicine): Long

    suspend fun deleteMedicine(id: Long)

    suspend fun getMedicineById(id: Long): Medicine?

    suspend fun simulateNewAlertForTelmisartan(): Boolean
}
