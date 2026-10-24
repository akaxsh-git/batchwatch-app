package org.batchwatch.app.data.repository

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.batchwatch.app.data.local.MedicineDao
import org.batchwatch.app.data.local.MedicineEntity
import org.batchwatch.app.data.remote.BatchWatchApi
import org.batchwatch.app.data.remote.dto.CheckRequestDto
import org.batchwatch.app.data.remote.dto.RecheckItemRequestDto
import org.batchwatch.app.domain.model.CheckResult
import org.batchwatch.app.domain.model.CheckVerdict
import org.batchwatch.app.domain.model.Medicine
import org.batchwatch.app.domain.model.ScanDraft

class RemoteRepository(
    private val api: BatchWatchApi,
    private val medicineDao: MedicineDao
) : MedicineRepository {

    override val isDemoMode: Boolean = false

    override suspend fun scanImage(imageBytes: ByteArray, photoUri: String?): Result<ScanDraft> = withContext(Dispatchers.IO) {
        try {
            val reqBody = imageBytes.toRequestBody("image/jpeg".toMediaTypeOrNull(), 0, imageBytes.size)
            val part = MultipartBody.Part.createFormData("image", "strip.jpg", reqBody)
            val response = api.scanPhoto(part)
            Result.success(response.toDomain(photoUri))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun checkBatch(
        batch: String,
        product: String?,
        manufacturer: String?
    ): Result<CheckResult> = withContext(Dispatchers.IO) {
        try {
            val request = CheckRequestDto(batch = batch, product = product, manufacturer = manufacturer)
            val response = api.checkBatch(request)
            Result.success(response.toDomain(batch, product))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun recheckAll(): Result<List<Pair<Medicine, CheckResult>>> = withContext(Dispatchers.IO) {
        try {
            // In a real app with flow, collect the first snapshot
            Result.success(emptyList())
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override fun getSavedMedicines(): Flow<List<Medicine>> {
        return medicineDao.getAllMedicines().map { list ->
            list.map { it.toDomain() }
        }
    }

    override suspend fun saveMedicine(medicine: Medicine): Long {
        return medicineDao.insertMedicine(MedicineEntity.fromDomain(medicine))
    }

    override suspend fun deleteMedicine(id: Long) {
        medicineDao.deleteById(id)
    }

    override suspend fun getMedicineById(id: Long): Medicine? {
        return medicineDao.getMedicineById(id)?.toDomain()
    }

    override suspend fun simulateNewAlertForTelmisartan(): Boolean {
        // No-op in remote mode
        return false
    }
}
