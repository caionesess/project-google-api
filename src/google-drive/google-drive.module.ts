import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { GOOGLE_DRIVE_FILES_REPOSITORY } from './interfaces/google-drive-files.repository.interface';
import { GoogleDriveFilesRepository } from './google-drive-files.repository';
import { GoogleDriveFilesController } from './google-drive-files.controller';
import { GoogleDriveFilesService } from './google-drive-files.service';

@Module({
  imports: [ConfigModule],
  controllers: [GoogleDriveFilesController],
  providers: [
    GoogleDriveFilesService,
    GoogleDriveFilesRepository,
    {
      provide: GOOGLE_DRIVE_FILES_REPOSITORY,
      useExisting: GoogleDriveFilesRepository,
    },
  ],
  exports: [GoogleDriveFilesService],
})
export class GoogleDriveModule {}
