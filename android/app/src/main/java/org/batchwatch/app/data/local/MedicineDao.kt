package org.batchwatch.app.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface MedicineDao {

    @Query("SELECT * FROM saved_medicines ORDER BY addedAt DESC")
    fun getAllMedicines(): Flow<List<MedicineEntity>>

    @Query("SELECT * FROM saved_medicines WHERE id = :id")
    suspend fun getMedicineById(id: Long): MedicineEntity?

    @Query("SELECT * FROM saved_medicines WHERE batch = :batch LIMIT 1")
    suspend fun getMedicineByBatch(batch: String): MedicineEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMedicine(entity: MedicineEntity): Long

    @Update
    suspend fun updateMedicine(entity: MedicineEntity)

    @Delete
    suspend fun deleteMedicine(entity: MedicineEntity)

    @Query("DELETE FROM saved_medicines WHERE id = :id")
    suspend fun deleteById(id: Long)

    @Query("SELECT COUNT(*) FROM saved_medicines")
    fun getCount(): Flow<Int>
}
