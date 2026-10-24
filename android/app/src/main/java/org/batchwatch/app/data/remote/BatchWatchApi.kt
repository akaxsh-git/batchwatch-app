package org.batchwatch.app.data.remote

import okhttp3.MultipartBody
import org.batchwatch.app.data.remote.dto.AlertVersionDto
import org.batchwatch.app.data.remote.dto.CheckRequestDto
import org.batchwatch.app.data.remote.dto.CheckResponseDto
import org.batchwatch.app.data.remote.dto.RecheckItemRequestDto
import org.batchwatch.app.data.remote.dto.RecheckResponseItemDto
import org.batchwatch.app.data.remote.dto.ScanResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface BatchWatchApi {

    @Multipart
    @POST("scan")
    suspend fun scanPhoto(
        @Part image: MultipartBody.Part
    ): ScanResponseDto

    @POST("check")
    suspend fun checkBatch(
        @Body request: CheckRequestDto
    ): CheckResponseDto

    @POST("recheck")
    suspend fun recheckMedicines(
        @Body items: List<RecheckItemRequestDto>
    ): List<RecheckResponseItemDto>

    @GET("alerts/version")
    suspend fun getAlertVersion(): AlertVersionDto
}
