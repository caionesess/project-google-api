import { BadRequestException, NotFoundException } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import {
  GOOGLE_DRIVE_FILES_REPOSITORY,
  type DriveFileSummary,
  type IGoogleDriveFilesRepository,
} from './interfaces/google-drive-files.repository.interface';
import { GoogleDriveFilesService } from './google-drive-files.service';

describe('GoogleDriveFilesService', () => {
  let service: GoogleDriveFilesService;
  let repository: jest.Mocked<IGoogleDriveFilesRepository>;

  beforeEach(async () => {
    repository = {
      upload: jest.fn(),
      updateMetadata: jest.fn(),
      moveToFolder: jest.fn(),
      delete: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        GoogleDriveFilesService,
        {
          provide: GOOGLE_DRIVE_FILES_REPOSITORY,
          useValue: repository,
        },
      ],
    }).compile();

    service = module.get(GoogleDriveFilesService);
  });

  describe('uploadFile', () => {
    it('rejeita buffer vazio', async () => {
      await expect(
        service.uploadFile({
          buffer: Buffer.alloc(0),
          originalName: 'a.txt',
          mimeType: 'text/plain',
        }),
      ).rejects.toBeInstanceOf(BadRequestException);
    });

    it('envia ao repositório e retorna resumo', async () => {
      const summary: DriveFileSummary = {
        id: 'id1',
        name: 'a.txt',
        mimeType: 'text/plain',
        parents: ['p1'],
      };
      repository.upload.mockResolvedValue(summary);

      const result = await service.uploadFile({
        buffer: Buffer.from('x'),
        originalName: 'a.txt',
        mimeType: 'text/plain',
        parents: ['p1'],
      });

      expect(result).toEqual(summary);
      expect(repository.upload).toHaveBeenCalledWith(
        expect.objectContaining({
          fileName: 'a.txt',
          mimeType: 'text/plain',
          parents: ['p1'],
        }),
      );
    });
  });

  describe('updateMetadata', () => {
    it('rejeita quando não há campos', async () => {
      await expect(service.updateMetadata('id', {})).rejects.toBeInstanceOf(BadRequestException);
    });

    it('propaga 404 como NotFoundException', async () => {
      repository.updateMetadata.mockRejectedValue({ code: 404, message: 'not found' });

      await expect(service.updateMetadata('id', { name: 'n' })).rejects.toBeInstanceOf(
        NotFoundException,
      );
    });
  });

  describe('moveToFolder', () => {
    it('rejeita targetFolderId vazio', async () => {
      await expect(service.moveToFolder('fid', '')).rejects.toBeInstanceOf(BadRequestException);
    });
  });

  describe('deleteFile', () => {
    it('chama repositório', async () => {
      repository.delete.mockResolvedValue(undefined);
      await service.deleteFile('fid');
      expect(repository.delete).toHaveBeenCalledWith('fid');
    });
  });
});
