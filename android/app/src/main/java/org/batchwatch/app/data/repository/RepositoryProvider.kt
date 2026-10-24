package org.batchwatch.app.data.repository

import android.content.Context
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import org.batchwatch.app.BuildConfig
import org.batchwatch.app.data.local.AppDatabase
import org.batchwatch.app.data.local.UserPreferences
import org.batchwatch.app.data.remote.BatchWatchApi
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

object RepositoryProvider {

    @Volatile
    private var repository: MedicineRepository? = null

    fun getRepository(context: Context): MedicineRepository {
        return repository ?: synchronized(this) {
            val database = AppDatabase.getInstance(context)
            val preferences = UserPreferences.create(context)

            val instance = if (BuildConfig.USE_DEMO) {
                DemoRepository(database.medicineDao(), preferences)
            } else {
                val logging = HttpLoggingInterceptor().apply {
                    level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
                }

                val okHttpClient = OkHttpClient.Builder()
                    .addInterceptor(logging)
                    .connectTimeout(25, TimeUnit.SECONDS)
                    .readTimeout(25, TimeUnit.SECONDS)
                    .writeTimeout(25, TimeUnit.SECONDS)
                    .build()

                val moshi = Moshi.Builder()
                    .add(KotlinJsonAdapterFactory())
                    .build()

                val retrofit = Retrofit.Builder()
                    .baseUrl(BuildConfig.BASE_URL)
                    .client(okHttpClient)
                    .addConverterFactory(MoshiConverterFactory.create(moshi))
                    .build()

                val api = retrofit.create(BatchWatchApi::class.java)
                RemoteRepository(api, database.medicineDao())
            }
            repository = instance
            instance
        }
    }
}
