import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Readable } from 'node:stream';
import { google } from 'googleapis';
import type { drive_v3 } from 'googleapis';
import type {
  DriveFileSummary,
  IGoogleDriveFilesRepository,
  UpdateDriveFileMetadataParams,
  UploadDriveFileParams,
} from './interfaces/google-drive-files.repository.interface';

const DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive'];

@Injectable()
export class GoogleDriveFilesRepository implements IGoogleDriveFilesRepository {
  private readonly logger = new Logger(GoogleDriveFilesRepository.name);
  private readonly drive: drive_v3.Drive;

  constructor(private readonly configService: ConfigService) {
    const credentialsPath = this.configService.get<string>('GOOGLE_APPLICATION_CREDENTIALS');

    const authConfig: { scopes: string[]; keyFile?: string } = {
      scopes: DRIVE_SCOPES,
    };

    if (credentialsPath) {
      authConfig.keyFile = credentialsPath;
    }

    const auth = new google.auth.GoogleAuth(authConfig);

    this.drive = google.drive({
      version: 'v3',
      auth,
    });
  }

  async upload(params: UploadDriveFileParams): Promise<DriveFileSummary> {
    const { buffer, fileName, mimeType, parents } = params;

    this.logger.log(
      JSON.stringify({
        msg: 'drive.upload.start',
        fileName,
        mimeType,
        sizeBytes: buffer.length,
        parentsCount: parents?.length ?? 0,
      }),
    );

    const requestBody: drive_v3.Schema$File = {
      name: fileName,
      parents: parents && parents.length > 0 ? parents : undefined,
    };

    const response = await this.drive.files.create({
      requestBody,
      media: {
        mimeType,
        body: Readable.from(buffer),
      },
      fields: 'id, name, mimeType, parents',
      supportsAllDrives: true,
    });

    const data = response.data;
    if (!data.id || !data.name) {
      throw new Error('Resposta inválida do Google Drive ao criar arquivo');
    }

    return this.toSummary(data);
  }

  async updateMetadata(
    fileId: string,
    params: UpdateDriveFileMetadataParams,
  ): Promise<DriveFileSummary> {
    this.logger.log(JSON.stringify({ msg: 'drive.updateMetadata.start', fileId }));

    const requestBody: drive_v3.Schema$File = {};
    if (params.name !== undefined) {
      requestBody.name = params.name;
    }
    if (params.description !== undefined) {
      requestBody.description = params.description;
    }

    const response = await this.drive.files.update({
      fileId,
      requestBody,
      fields: 'id, name, mimeType, parents',
      supportsAllDrives: true,
    });

    const data = response.data;
    if (!data.id || !data.name) {
      throw new Error('Resposta inválida do Google Drive ao atualizar arquivo');
    }

    return this.toSummary(data);
  }

  async moveToFolder(fileId: string, targetFolderId: string): Promise<DriveFileSummary> {
    this.logger.log(
      JSON.stringify({ msg: 'drive.move.start', fileId, targetFolderId }),
    );

    const current = await this.drive.files.get({
      fileId,
      fields: 'parents',
      supportsAllDrives: true,
    });

    const previousParents = (current.data.parents ?? []).join(',');

    const response = await this.drive.files.update({
      fileId,
      addParents: targetFolderId,
      ...(previousParents ? { removeParents: previousParents } : {}),
      fields: 'id, name, mimeType, parents',
      supportsAllDrives: true,
    });

    const data = response.data;
    if (!data.id || !data.name) {
      throw new Error('Resposta inválida do Google Drive ao mover arquivo');
    }

    return this.toSummary(data);
  }

  async delete(fileId: string): Promise<void> {
    this.logger.log(JSON.stringify({ msg: 'drive.delete.start', fileId }));

    await this.drive.files.delete({
      fileId,
      supportsAllDrives: true,
    });
  }

  private toSummary(data: drive_v3.Schema$File): DriveFileSummary {
    return {
      id: data.id!,
      name: data.name!,
      mimeType: data.mimeType ?? 'application/octet-stream',
      parents: data.parents ?? undefined,
    };
  }
}
