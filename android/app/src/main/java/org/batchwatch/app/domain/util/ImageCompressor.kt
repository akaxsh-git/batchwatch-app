package org.batchwatch.app.domain.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.InputStream
import kotlin.math.max

object ImageCompressor {

    private const val MAX_DIMENSION = 1600
    private const val JPEG_QUALITY = 85

    suspend fun compressUri(context: Context, uri: Uri): ByteArray = withContext(Dispatchers.IO) {
        val inputStream: InputStream = context.contentResolver.openInputStream(uri)
            ?: throw IllegalArgumentException("Cannot open image stream for $uri")

        val rawBytes = inputStream.use { it.readBytes() }
        compressBytes(rawBytes)
    }

    suspend fun compressBytes(bytes: ByteArray): ByteArray = withContext(Dispatchers.Default) {
        // Decode bounds only first
        val options = BitmapFactory.Options().apply {
            inJustDecodeBounds = true
        }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, options)

        val width = options.outWidth
        val height = options.outHeight
        val maxSide = max(width, height)

        var sampleSize = 1
        if (maxSide > MAX_DIMENSION) {
            sampleSize = maxSide / MAX_DIMENSION
        }

        // Full decode with downsampling
        val decodeOptions = BitmapFactory.Options().apply {
            inSampleSize = sampleSize
        }
        val sampledBitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size, decodeOptions)
            ?: throw IllegalStateException("Failed to decode image bytes into bitmap")

        // Further scale if still larger than max dimension
        val currentMax = max(sampledBitmap.width, sampledBitmap.height)
        val finalBitmap = if (currentMax > MAX_DIMENSION) {
            val scale = MAX_DIMENSION.toFloat() / currentMax
            val matrix = Matrix().apply { postScale(scale, scale) }
            Bitmap.createBitmap(sampledBitmap, 0, 0, sampledBitmap.width, sampledBitmap.height, matrix, true)
        } else {
            sampledBitmap
        }

        val outputStream = ByteArrayOutputStream()
        finalBitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, outputStream)
        outputStream.toByteArray()
    }
}
